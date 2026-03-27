from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, View
from django.contrib import messages
from .models import TuroTrip, Investor, Vehicle
from .utils.importer import import_turo_csv
from django.db.models import Sum, Count, Avg, Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from decimal import Decimal

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

class UploadCSVView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

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
