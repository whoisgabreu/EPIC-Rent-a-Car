from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, View
from django.contrib import messages
from .models import TuroTrip
from .utils.importer import import_turo_csv
from django.db.models import Sum, Count, Avg

# ... (rest of imports)

class DashboardView(TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trips = TuroTrip.objects.all()
        
        # Basic Metrics
        context['total_earnings'] = trips.aggregate(Sum('total_earnings'))['total_earnings__sum'] or 0
        context['total_trips'] = trips.count()
        context['avg_earnings'] = trips.aggregate(Avg('total_earnings'))['total_earnings__avg'] or 0
        context['total_days'] = trips.aggregate(Sum('trip_days'))['trip_days__sum'] or 0
        
        # Recent Trips
        context['recent_trips'] = trips[:10]
        
        # Vehicle Stats
        context['vehicle_stats'] = trips.values('vehicle_name').annotate(
            count=Count('id'),
            earnings=Sum('total_earnings')
        ).order_by('-earnings')
        
        return context

class UploadCSVView(View):
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
