from django.db import models

class TuroTrip(models.Model):
    # Basic Info
    reservation_id = models.CharField(max_length=50, unique=True, verbose_name="ID da Reserva")
    guest = models.CharField(max_length=255, verbose_name="Hóspede")
    vehicle = models.CharField(max_length=255, verbose_name="Veículo")
    vehicle_name = models.CharField(max_length=255, verbose_name="Nome do Veículo")
    vehicle_id = models.CharField(max_length=50, verbose_name="ID do Veículo")
    vin = models.CharField(max_length=50, verbose_name="VIN")
    
    # Dates
    start_date = models.DateTimeField(verbose_name="Início da Viagem")
    end_date = models.DateTimeField(verbose_name="Fim da Viagem")
    
    # Locations
    pickup_location = models.TextField(verbose_name="Local de Retirada")
    return_location = models.TextField(verbose_name="Local de Devolução")
    
    # Status
    trip_status = models.CharField(max_length=100, verbose_name="Status da Viagem")
    
    # Odometer and Distance
    check_in_odometer = models.IntegerField(null=True, blank=True, verbose_name="Odômetro Check-in")
    check_out_odometer = models.IntegerField(null=True, blank=True, verbose_name="Odômetro Check-out")
    distance_traveled = models.IntegerField(null=True, blank=True, verbose_name="Distância Percorrida")
    
    # Earnings and Fees (DecimalFields for currency)
    trip_days = models.IntegerField(verbose_name="Dias de Viagem")
    trip_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço da Viagem")
    boost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Preço Boost")
    
    # Discounts
    discount_3_day = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Desconto 3 dias")
    discount_1_week = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Desconto 1 semana")
    discount_2_week = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Desconto 2 semanas")
    discount_3_week = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Desconto 3 semanas")
    discount_1_month = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Desconto 1 mês")
    discount_2_month = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Desconto 2 meses")
    discount_3_month = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Desconto 3 meses")
    discount_non_refundable = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Desconto Não Reembolsável")
    discount_early_bird = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Desconto Early Bird")
    
    # Credits and Fees
    host_promotional_credit = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Crédito Promocional Host")
    delivery = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Entrega")
    excess_distance = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Distância Excedente")
    extras = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Extras")
    cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Taxa de Cancelamento")
    additional_usage = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Uso Adicional")
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Taxa de Atraso")
    improper_return_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Taxa de Devolução Inadequada")
    airport_operations_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Taxa de Operação Aeroportuária")
    airport_parking_credit = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Crédito de Estacionamento Aeroporto")
    tolls_and_tickets = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Pedágios e Multas de Trânsito")
    on_trip_ev_charging = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Carregamento EV em Viagem")
    post_trip_ev_charging = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Carregamento EV pós Viagem")
    smoking_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Taxa de Fumo")
    cleaning_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Taxa de Limpeza")
    fines_paid_to_host = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Multas pagas ao Host")
    gas_reimbursement = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Reembolso de Combustível")
    gas_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Taxa de Combustível")
    other_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Outras Taxas")
    sales_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Imposto sobre Vendas")
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ganhos Totais")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Viagem"
        verbose_name_plural = "Viagens"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.reservation_id} - {self.vehicle_name} ({self.guest})"
