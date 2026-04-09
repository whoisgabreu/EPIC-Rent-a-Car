from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, View, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.http import HttpResponse
from .models import TuroTrip, Investor, Vehicle
from .forms import UserCreateForm, UserUpdateForm, InvestorForm, VehicleForm
from .utils.importer import import_turo_csv
from .utils.report_service import build_report_context
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from decimal import Decimal
from django.utils import timezone
from django.template.loader import render_to_string
from datetime import date as _date
import weasyprint

# ── Profit Split Constants ─────────────────────────────────────────
# Change these values to update the profit split across the entire system.
INVESTOR_PROFIT_SHARE = Decimal('0.50')  # Investor's share of operational result
EPIC_PROFIT_SHARE     = Decimal('0.50')  # EPIC's commission share
# ──────────────────────────────────────────────────────────────────
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin that restricts access to admin (is_staff) users only."""
    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "Access restricted to administrators.")
        return redirect('dashboard')

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        is_admin = user.is_staff or user.is_superuser
        investor = None
        selected_investor_id = self.request.GET.get('investor_id')
        
        if is_admin:
            if selected_investor_id:
                investor = Investor.objects.filter(id=selected_investor_id).first()
            context['all_investors'] = Investor.objects.all().order_by('name')
        else:
            try:
                investor = user.investor_profile
            except:
                context['no_profile'] = True
                return context

        # Base filters
        if is_admin and not selected_investor_id:
            # Global view
            vehicles = Vehicle.objects.all()
            trips = TuroTrip.objects.all()
        elif investor:
            # Filtered view (by specific investor)
            vehicles = Vehicle.objects.filter(investor=investor)
            trips = TuroTrip.objects.filter(vehicle_obj__in=vehicles)
        else:
            vehicles = Vehicle.objects.none()
            trips = TuroTrip.objects.none()

        context['is_admin'] = is_admin
        context['investor'] = investor
        context['selected_investor_id'] = selected_investor_id
        
        # ── Period Filter (YYYY-MM from end_date) ─────────────────────
        # Build list of available months from trip end_date
        available_months_qs = (
            TuroTrip.objects
            .filter(end_date__isnull=False)
            .annotate(month=TruncMonth('end_date'))
            .values_list('month', flat=True)
            .distinct()
            .order_by('-month')
        )
        available_periods = []
        for m in available_months_qs:
            if m:
                available_periods.append(m.strftime('%Y-%m'))
        context['available_periods'] = available_periods

        selected_period = self.request.GET.get('period', 'all')
        context['selected_period'] = selected_period

        if selected_period != 'all':
            try:
                p_year, p_month = map(int, selected_period.split('-'))
                trips = trips.filter(end_date__year=p_year, end_date__month=p_month)
            except (ValueError, AttributeError):
                pass  # fallback to unfiltered

        # Active trips: only statuses that generate revenue
        ACTIVE_STATUSES = ['Completed', 'Booked', 'In-progress']
        active_trips = trips.filter(trip_status__in=ACTIVE_STATUSES)

        # Split Realized and Forecast (for informational breakdown)
        realized_trips = active_trips.filter(trip_status='Completed')
        forecast_trips = active_trips.filter(trip_status__in=['Booked', 'In-progress'])

        # Forecast Metrics
        forecast_metrics = forecast_trips.aggregate(
            total_trip_price=Sum('trip_price'),
            total_boost_price=Sum('boost_price')
        )
        context['forecast_revenue'] = (forecast_metrics['total_trip_price'] or Decimal('0.00')) + \
                                      (forecast_metrics['total_boost_price'] or Decimal('0.00'))

        # Operations Metrics (Realized)
        metrics = realized_trips.aggregate(
            total_trip_price=Sum('trip_price'),
            total_boost_price=Sum('boost_price'),
            total_earnings=Sum('total_earnings'),
            total_delivery=Sum('delivery'),
            total_excess_distance=Sum('excess_distance'),
            total_extras=Sum('extras'),
            total_cancellation_fee=Sum('cancellation_fee'),
            total_additional_usage=Sum('additional_usage'),
            total_late_fee=Sum('late_fee'),
            total_improper_return_fee=Sum('improper_return_fee'),
            total_airport_operations_fee=Sum('airport_operations_fee'),
            total_airport_parking_credit=Sum('airport_parking_credit'),
            total_tolls_and_tickets=Sum('tolls_and_tickets'),
            total_on_trip_ev_charging=Sum('on_trip_ev_charging'),
            total_post_trip_ev_charging=Sum('post_trip_ev_charging'),
            total_smoking_fee=Sum('smoking_fee'),
            total_cleaning_fee=Sum('cleaning_fee'),
            total_fines_paid_to_host=Sum('fines_paid_to_host'),
            total_gas_reimbursement=Sum('gas_reimbursement'),
            total_gas_fee=Sum('gas_fee'),
            total_other_fees=Sum('other_fees'),
            total_sales_tax=Sum('sales_tax'),
            count=Count('id'),
            days=Sum('trip_days')
        )
        
        # Financial Totals (Gross Earnings = Total Earnings)
        gross_earnings = metrics['total_earnings'] or Decimal('0.00')
        
        # PO Calculation deductions
        base_earnings = gross_earnings
        deductions_list = [
            metrics['total_delivery'], metrics['total_excess_distance'], metrics['total_extras'],
            metrics['total_cancellation_fee'], metrics['total_additional_usage'], metrics['total_late_fee'],
            metrics['total_improper_return_fee'], metrics['total_airport_operations_fee'],
            metrics['total_airport_parking_credit'], metrics['total_tolls_and_tickets'],
            metrics['total_on_trip_ev_charging'], metrics['total_post_trip_ev_charging'],
            metrics['total_smoking_fee'], metrics['total_cleaning_fee'], metrics['total_fines_paid_to_host'],
            metrics['total_gas_reimbursement'], metrics['total_gas_fee'], metrics['total_other_fees'],
            metrics['total_sales_tax']
        ]
        total_deductions = sum([d or Decimal('0.00') for d in deductions_list])
        
        # Result Calculation (PO Formula)
        resultado_operacional = base_earnings - total_deductions
        investor_share = resultado_operacional * INVESTOR_PROFIT_SHARE
        epic_share = resultado_operacional * EPIC_PROFIT_SHARE

        context['metrics'] = {
            'gross_earnings': gross_earnings,
            'resultado_operacional': resultado_operacional,
            'investor_share': investor_share,
            'epic_share': epic_share,
            'total_trips': metrics['count'] or 0,
            'total_days': metrics['days'] or 0,
            'adr': gross_earnings / metrics['days'] if metrics['days'] and metrics['days'] > 0 else 0,
            'expenses': {
                'tolls': metrics['total_tolls_and_tickets'] or Decimal('0.00'),
                'parking': metrics['total_airport_parking_credit'] or Decimal('0.00'),
                'cleaning': metrics['total_cleaning_fee'] or Decimal('0.00'),
                'gas': metrics['total_gas_reimbursement'] or Decimal('0.00'),
            }
        }
        
        # Check unmapped vehicles for Admin
        if is_admin:
            unmapped_qs = TuroTrip.objects.filter(vehicle_obj__isnull=True).values('vin', 'vehicle_name', 'plate_extracted')
            unmapped_dict = {}
            for item in unmapped_qs:
                vin = item['vin']
                if vin and vin not in unmapped_dict:
                    unmapped_dict[vin] = {
                        'vin': vin,
                        'name': item['vehicle_name'],
                        'plate': item['plate_extracted']
                    }
            context['unmapped_vehicles'] = list(unmapped_dict.values())

        context['recent_trips'] = trips[:10]
        
        # Vehicle Stats using relationships
        vehicle_stats = []
        for v in vehicles:
            v_trips = realized_trips.filter(vehicle_obj=v)
            v_metrics = v_trips.aggregate(
                count=Count('id'),
                days=Sum('trip_days'),
                te=Sum('total_earnings'),
                d1=Sum('delivery'), d2=Sum('excess_distance'), d3=Sum('extras'),
                d4=Sum('cancellation_fee'), d5=Sum('additional_usage'), d6=Sum('late_fee'),
                d7=Sum('improper_return_fee'), d8=Sum('airport_operations_fee'),
                d9=Sum('airport_parking_credit'), d10=Sum('tolls_and_tickets'),
                d11=Sum('on_trip_ev_charging'), d12=Sum('post_trip_ev_charging'),
                d13=Sum('smoking_fee'), d14=Sum('cleaning_fee'), d15=Sum('fines_paid_to_host'),
                d16=Sum('gas_reimbursement'), d17=Sum('gas_fee'), d18=Sum('other_fees'),
                d19=Sum('sales_tax')
            )
            v_count = v_metrics['count'] or 0
            v_days = v_metrics['days'] or 0
            v_avg_days = v_days / v_count if v_count > 0 else 0
            
            v_base = v_metrics['te'] or Decimal('0.00')
            v_deds = sum([v_metrics[f'd{i}'] or Decimal('0.00') for i in range(1, 20)])
            v_res = v_base - v_deds
            
            vehicle_stats.append({
                'name': v.year_make_model,
                'plate': v.plate,
                'vin': v.vin,
                'trips': v_count,
                'avg_trip_days': round(v_avg_days, 1),
                'earnings': v_res,
                'investor_share': v_res * INVESTOR_PROFIT_SHARE
            })
            
        context['vehicle_stats'] = sorted(vehicle_stats, key=lambda x: x['investor_share'], reverse=True)
        return context

# ══════════════════════════════════════════════════════════════════
#  INVESTOR PORTFOLIO REPORT  (PDF download)
# ══════════════════════════════════════════════════════════════════

class InvestorReportView(LoginRequiredMixin, View):
    """
    GET /report/?investor_id=<id>&date_filter=<all_time|current_month>
              &date_from=YYYY-MM-DD&date_to=YYYY-MM-DD

    - Regular investors can only generate their own report.
    - Admins can pass investor_id to generate for any investor.
    """

    def get(self, request):
        user = request.user
        is_admin = user.is_staff or user.is_superuser

        # Resolve investor
        investor_id = request.GET.get('investor_id')
        if is_admin and investor_id:
            investor = get_object_or_404(Investor, pk=investor_id)
        else:
            try:
                investor = user.investor_profile
            except Exception:
                messages.error(request, 'No investor profile linked to your account.')
                return redirect('dashboard')

        # Date params
        date_filter = request.GET.get('date_filter', 'all_time')
        period = request.GET.get('period')
        date_from = None
        date_to = None
        raw_from = request.GET.get('date_from')
        raw_to   = request.GET.get('date_to')
        if raw_from and raw_to:
            try:
                date_from = _date.fromisoformat(raw_from)
                date_to   = _date.fromisoformat(raw_to)
            except ValueError:
                pass

        # Build context
        ctx = build_report_context(
            investor=investor,
            date_filter=date_filter,
            date_from=date_from,
            date_to=date_to,
            period=period,
        )
        ctx['generated_at'] = timezone.now().strftime('%b %d, %Y  %H:%M UTC')

        # Render HTML → PDF
        html_string = render_to_string('reports/investor_report.html', ctx, request=request)
        pdf_bytes = weasyprint.HTML(
            string=html_string,
            base_url=request.build_absolute_uri('/')
        ).write_pdf()

        # Dynamic filename
        safe_name = investor.name.replace(' ', '_')
        period_tag = ctx['period_label'].replace(' ', '_').replace('–', '-')
        filename = f'report_{safe_name}_{period_tag}.pdf'

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class UploadCSVView(AdminRequiredMixin, View):
    def get(self, request):
        return render(request, 'dashboard/upload.html')

    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, "No file uploaded.")
            return redirect('upload_csv')
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "The file must be a CSV.")
            return redirect('upload_csv')
        try:
            count = import_turo_csv(csv_file)
            messages.success(request, f"Success! {count} records processed.")
        except Exception as e:
            messages.error(request, f"Error processing CSV: {str(e)}")
        return redirect('dashboard')


# ══════════════════════════════════════════════════════════════════
#  ADMIN MANAGEMENT AREA
# ══════════════════════════════════════════════════════════════════

class AdminPanelView(AdminRequiredMixin, TemplateView):
    template_name = 'dashboard/admin/panel.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_users'] = User.objects.count()
        ctx['total_investors'] = Investor.objects.count()
        ctx['total_vehicles'] = Vehicle.objects.count()
        ctx['inactive_vehicles'] = Vehicle.objects.filter(status='Inactive').count()
        ctx['unlinked_investors'] = Investor.objects.filter(user__isnull=True).count()
        return ctx


# ── Users ─────────────────────────────────────────────────────────

class UserListView(AdminRequiredMixin, ListView):
    template_name = 'dashboard/admin/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.all().order_by('username')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
        return qs


class UserCreateView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/user_form.html'

    def get(self, request):
        return render(request, self.template_name, {'form': UserCreateForm(), 'action': 'Create'})

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User created successfully.")
            return redirect('admin_user_list')
        return render(request, self.template_name, {'form': form, 'action': 'Create'})


class UserUpdateView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/user_form.html'

    def get_object(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        user_obj = self.get_object(pk)
        form = UserUpdateForm(instance=user_obj)
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': user_obj})

    def post(self, request, pk):
        user_obj = self.get_object(pk)
        form = UserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated successfully.")
            return redirect('admin_user_list')
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': user_obj})


class UserDeleteView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/confirm_delete.html'

    def get_object(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        return render(request, self.template_name, {
            'object': obj, 'object_type': 'User',
            'cancel_url': reverse_lazy('admin_user_list')
        })

    def post(self, request, pk):
        obj = self.get_object(pk)
        if obj == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect('admin_user_list')
        obj.delete()
        messages.success(request, "User deleted.")
        return redirect('admin_user_list')


# ── Investors ─────────────────────────────────────────────────────

class InvestorListView(AdminRequiredMixin, ListView):
    template_name = 'dashboard/admin/investor_list.html'
    context_object_name = 'investors'
    paginate_by = 20

    def get_queryset(self):
        qs = Investor.objects.prefetch_related('owned_vehicles').order_by('name')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(name__icontains=q)
        return qs


class InvestorCreateView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/investor_form.html'

    def get(self, request):
        return render(request, self.template_name, {'form': InvestorForm(), 'action': 'Create'})

    def post(self, request):
        form = InvestorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Investor created successfully.")
            return redirect('admin_investor_list')
        return render(request, self.template_name, {'form': form, 'action': 'Create'})


class InvestorUpdateView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/investor_form.html'

    def get_object(self, pk):
        return get_object_or_404(Investor, pk=pk)

    def get(self, request, pk):
        investor = self.get_object(pk)
        form = InvestorForm(instance=investor)
        return render(request, self.template_name, {
            'form': form, 'action': 'Edit', 'object': investor,
            'vehicles': investor.owned_vehicles.all()
        })

    def post(self, request, pk):
        investor = self.get_object(pk)
        form = InvestorForm(request.POST, instance=investor)
        if form.is_valid():
            form.save()
            messages.success(request, "Investor updated.")
            return redirect('admin_investor_list')
        return render(request, self.template_name, {
            'form': form, 'action': 'Edit', 'object': investor,
            'vehicles': investor.owned_vehicles.all()
        })


class InvestorDeleteView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/confirm_delete.html'

    def get_object(self, pk):
        return get_object_or_404(Investor, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        return render(request, self.template_name, {
            'object': obj, 'object_type': 'Investor',
            'cancel_url': reverse_lazy('admin_investor_list')
        })

    def post(self, request, pk):
        self.get_object(pk).delete()
        messages.success(request, "Investor deleted.")
        return redirect('admin_investor_list')


# ── Vehicles ──────────────────────────────────────────────────────

class VehicleListView(AdminRequiredMixin, ListView):
    template_name = 'dashboard/admin/vehicle_list.html'
    context_object_name = 'vehicles'
    paginate_by = 20

    def get_queryset(self):
        qs = Vehicle.objects.select_related('investor').order_by('year_make_model')
        q = self.request.GET.get('q')
        investor_id = self.request.GET.get('investor_id')
        if q:
            qs = qs.filter(
                Q(year_make_model__icontains=q) | Q(plate__icontains=q) | Q(vin__icontains=q)
            )
        if investor_id:
            qs = qs.filter(investor_id=investor_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['all_investors'] = Investor.objects.order_by('name')
        ctx['selected_investor_id'] = self.request.GET.get('investor_id', '')
        return ctx


class VehicleCreateView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/vehicle_form.html'

    def get(self, request):
        initial_data = {}
        vin_param = request.GET.get('vin')
        name_param = request.GET.get('name')
        plate_param = request.GET.get('plate')
        if vin_param:
            initial_data['vin'] = vin_param
        if name_param:
            initial_data['year_make_model'] = name_param
        if plate_param:
            initial_data['plate'] = plate_param
            
        form = VehicleForm(initial=initial_data)
        return render(request, self.template_name, {'form': form, 'action': 'Create'})

    def post(self, request):
        form = VehicleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle created successfully.")
            return redirect('admin_vehicle_list')
        return render(request, self.template_name, {'form': form, 'action': 'Create'})


class VehicleUpdateView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/vehicle_form.html'

    def get_object(self, pk):
        return get_object_or_404(Vehicle, pk=pk)

    def get(self, request, pk):
        vehicle = self.get_object(pk)
        form = VehicleForm(instance=vehicle)
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': vehicle})

    def post(self, request, pk):
        vehicle = self.get_object(pk)
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle updated.")
            return redirect('admin_vehicle_list')
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': vehicle})


class VehicleDeleteView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/confirm_delete.html'

    def get_object(self, pk):
        return get_object_or_404(Vehicle, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        return render(request, self.template_name, {
            'object': obj, 'object_type': 'Vehicle',
            'cancel_url': reverse_lazy('admin_vehicle_list')
        })

    def post(self, request, pk):
        self.get_object(pk).delete()
        messages.success(request, "Vehicle deleted.")
        return redirect('admin_vehicle_list')
