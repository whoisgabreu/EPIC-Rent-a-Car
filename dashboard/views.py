from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, View, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from .models import TuroTrip, Investor, Vehicle
from .forms import UserCreateForm, UserUpdateForm, InvestorForm, VehicleForm
from .utils.importer import import_turo_csv
from django.db.models import Sum, Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from decimal import Decimal


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin that restricts access to admin (is_staff) users only."""
    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "Acesso restrito a administradores.")
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
        
        # Operational Metrics (from TuroTrip)
        metrics = trips.aggregate(
            total_trip_price=Sum('trip_price'),
            total_boost_price=Sum('boost_price'),
            total_extras=Sum('extras'),
            total_tolls_turo=Sum('tolls_and_tickets'),
            total_parking_turo=Sum('airport_parking_credit'),
            total_cleaning=Sum('cleaning_fee'),
            total_gas=Sum('gas_reimbursement'),
            count=Count('id'),
            days=Sum('trip_days')
        )
        
        # Financial Totals
        total_trip_price = metrics['total_trip_price'] or Decimal('0.00')
        total_boost_price = metrics['total_boost_price'] or Decimal('0.00')
        gross_earnings = total_trip_price + total_boost_price
        
        # Expenses and Tolls from official Turo data
        tolls_turo = metrics['total_tolls_turo'] or Decimal('0.00')
        parking_turo = metrics['total_parking_turo'] or Decimal('0.00')
        extras_turo = metrics['total_extras'] or Decimal('0.00')
        
        # Result Calculation (PO Formula)
        resultado_operacional = gross_earnings - extras_turo - tolls_turo - parking_turo
        
        investor_share = resultado_operacional * Decimal('0.60')
        epic_share = resultado_operacional * Decimal('0.40')

        context['metrics'] = {
            'gross_earnings': gross_earnings,
            'resultado_operacional': resultado_operacional,
            'investor_share': investor_share,
            'epic_share': epic_share,
            'total_trips': metrics['count'] or 0,
            'total_days': metrics['days'] or 0,
            'adr': gross_earnings / metrics['days'] if metrics['days'] and metrics['days'] > 0 else 0,
            'expenses': {
                'tolls': tolls_turo,
                'parking': parking_turo,
                'extras': extras_turo,
                'cleaning': metrics['total_cleaning'] or 0,
                'gas': metrics['total_gas'] or 0,
            }
        }
        
        context['recent_trips'] = trips[:10]
        
        # Vehicle Stats using relationships
        vehicle_stats = []
        for v in vehicles:
            v_trips = trips.filter(vehicle_obj=v)
            v_metrics = v_trips.aggregate(
                tp=Sum('trip_price'),
                bp=Sum('boost_price'),
                ex=Sum('extras'),
                tl=Sum('tolls_and_tickets'),
                pk=Sum('airport_parking_credit')
            )
            v_gross = (v_metrics['tp'] or 0) + (v_metrics['bp'] or 0)
            v_res = v_gross - (v_metrics['ex'] or 0) - (v_metrics['tl'] or 0) - (v_metrics['pk'] or 0)
            
            vehicle_stats.append({
                'name': v.year_make_model,
                'plate': v.plate,
                'vin': v.vin,
                'trips': v_trips.count(),
                'earnings': v_res,
                'investor_share': v_res * Decimal('0.60')
            })
            
        context['vehicle_stats'] = sorted(vehicle_stats, key=lambda x: x['earnings'], reverse=True)
        return context

class UploadCSVView(AdminRequiredMixin, View):
    def get(self, request):
        return render(request, 'dashboard/upload.html')

    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, "Nenhum arquivo enviado.")
            return redirect('upload_csv')
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "O arquivo deve ser um CSV.")
            return redirect('upload_csv')
        try:
            count = import_turo_csv(csv_file)
            messages.success(request, f"Sucesso! {count} registros processados.")
        except Exception as e:
            messages.error(request, f"Erro ao processar CSV: {str(e)}")
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
        return render(request, self.template_name, {'form': UserCreateForm(), 'action': 'Criar'})

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuário criado com sucesso.")
            return redirect('admin_user_list')
        return render(request, self.template_name, {'form': form, 'action': 'Criar'})


class UserUpdateView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/user_form.html'

    def get_object(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        user_obj = self.get_object(pk)
        form = UserUpdateForm(instance=user_obj)
        return render(request, self.template_name, {'form': form, 'action': 'Editar', 'object': user_obj})

    def post(self, request, pk):
        user_obj = self.get_object(pk)
        form = UserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuário atualizado com sucesso.")
            return redirect('admin_user_list')
        return render(request, self.template_name, {'form': form, 'action': 'Editar', 'object': user_obj})


class UserDeleteView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/confirm_delete.html'

    def get_object(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        return render(request, self.template_name, {
            'object': obj, 'object_type': 'Usuário',
            'cancel_url': reverse_lazy('admin_user_list')
        })

    def post(self, request, pk):
        obj = self.get_object(pk)
        if obj == request.user:
            messages.error(request, "Você não pode excluir sua própria conta.")
            return redirect('admin_user_list')
        obj.delete()
        messages.success(request, "Usuário excluído.")
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
        return render(request, self.template_name, {'form': InvestorForm(), 'action': 'Criar'})

    def post(self, request):
        form = InvestorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Investidor criado com sucesso.")
            return redirect('admin_investor_list')
        return render(request, self.template_name, {'form': form, 'action': 'Criar'})


class InvestorUpdateView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/investor_form.html'

    def get_object(self, pk):
        return get_object_or_404(Investor, pk=pk)

    def get(self, request, pk):
        investor = self.get_object(pk)
        form = InvestorForm(instance=investor)
        return render(request, self.template_name, {
            'form': form, 'action': 'Editar', 'object': investor,
            'vehicles': investor.owned_vehicles.all()
        })

    def post(self, request, pk):
        investor = self.get_object(pk)
        form = InvestorForm(request.POST, instance=investor)
        if form.is_valid():
            form.save()
            messages.success(request, "Investidor atualizado.")
            return redirect('admin_investor_list')
        return render(request, self.template_name, {
            'form': form, 'action': 'Editar', 'object': investor,
            'vehicles': investor.owned_vehicles.all()
        })


class InvestorDeleteView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/confirm_delete.html'

    def get_object(self, pk):
        return get_object_or_404(Investor, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        return render(request, self.template_name, {
            'object': obj, 'object_type': 'Investidor',
            'cancel_url': reverse_lazy('admin_investor_list')
        })

    def post(self, request, pk):
        self.get_object(pk).delete()
        messages.success(request, "Investidor excluído.")
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
        return render(request, self.template_name, {'form': VehicleForm(), 'action': 'Criar'})

    def post(self, request):
        form = VehicleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Veículo criado com sucesso.")
            return redirect('admin_vehicle_list')
        return render(request, self.template_name, {'form': form, 'action': 'Criar'})


class VehicleUpdateView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/vehicle_form.html'

    def get_object(self, pk):
        return get_object_or_404(Vehicle, pk=pk)

    def get(self, request, pk):
        vehicle = self.get_object(pk)
        form = VehicleForm(instance=vehicle)
        return render(request, self.template_name, {'form': form, 'action': 'Editar', 'object': vehicle})

    def post(self, request, pk):
        vehicle = self.get_object(pk)
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, "Veículo atualizado.")
            return redirect('admin_vehicle_list')
        return render(request, self.template_name, {'form': form, 'action': 'Editar', 'object': vehicle})


class VehicleDeleteView(AdminRequiredMixin, View):
    template_name = 'dashboard/admin/confirm_delete.html'

    def get_object(self, pk):
        return get_object_or_404(Vehicle, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        return render(request, self.template_name, {
            'object': obj, 'object_type': 'Veículo',
            'cancel_url': reverse_lazy('admin_vehicle_list')
        })

    def post(self, request, pk):
        self.get_object(pk).delete()
        messages.success(request, "Veículo excluído.")
        return redirect('admin_vehicle_list')
