from django.db import models
from django.contrib.auth.models import User

class Investor(models.Model):
    user = models.OneToOneField(User, related_name='investor_profile', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, unique=True, verbose_name="Investor Name")
    status = models.CharField(max_length=50, default='Active', verbose_name="Status")

    
    class Meta:
        verbose_name = "Investor"
        verbose_name_plural = "Investors"

    def __str__(self):
        return self.name

class Vehicle(models.Model):
    vin = models.CharField(max_length=50, unique=True, verbose_name="VIN")
    plate = models.CharField(max_length=20, verbose_name="License Plate")
    year_make_model = models.CharField(max_length=255, verbose_name="Year/Make/Model")
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='owned_vehicles', verbose_name="Investor")
    status = models.CharField(max_length=50, default='Active', verbose_name="Status")
    acquisition_date = models.DateField(null=True, blank=True, verbose_name="Acquisition Date")
    
    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"

    def __str__(self):
        return f"{self.year_make_model} ({self.plate})"

class Period(models.Model):
    period_key = models.CharField(max_length=20, unique=True, verbose_name="Period Key (YYYY-MM)")
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")

    class Meta:
        verbose_name = "Period"
        verbose_name_plural = "Periods"
        ordering = ['-start_date']

    def __str__(self):
        return self.period_key

class Investment(models.Model):
    name = models.CharField(max_length=255, verbose_name="Investment Name")
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='investments', verbose_name="Investor")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='investments', verbose_name="Vehicle")
    ownership_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, verbose_name="Ownership Percentage (%)")
    invested_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Invested Amount")
    start_date = models.DateField(verbose_name="Start Date")
    duration_days = models.IntegerField(null=True, blank=True, verbose_name="Duration (Days)")

    class Meta:
        verbose_name = "Investment"
        verbose_name_plural = "Investments"

    def __str__(self):
        return f"{self.name} - {self.investor.name}"

class Expense(models.Model):
    EXPENSE_TYPES = [
        ('Maintenance', 'Maintenance'),
        ('Repair', 'Repair'),
        ('Cleaning', 'Cleaning'),
        ('Gas', 'Gas'),
        ('Insurance', 'Insurance'),
        ('Other', 'Other'),
    ]
    name = models.CharField(max_length=255, verbose_name="Expense Name")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='expenses', verbose_name="Vehicle")
    period = models.ForeignKey(Period, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses', verbose_name="Period")
    expense_type = models.CharField(max_length=50, choices=EXPENSE_TYPES, verbose_name="Expense Type")
    date = models.DateField(verbose_name="Date")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount")
    description = models.TextField(null=True, blank=True, verbose_name="Description")
    status = models.CharField(max_length=50, default='Approved', verbose_name="Status")
    payment_status = models.CharField(max_length=50, default='Paid', verbose_name="Payment Status")

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"

    def __str__(self):
        return f"{self.name} - {self.vehicle.plate} ({self.amount})"

class Toll(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='tolls', verbose_name="Vehicle")
    period = models.ForeignKey(Period, on_delete=models.SET_NULL, null=True, blank=True, related_name='tolls', verbose_name="Period")
    plate = models.CharField(max_length=20, verbose_name="License Plate")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount")
    date = models.DateField(verbose_name="Date")

    class Meta:
        verbose_name = "Toll"
        verbose_name_plural = "Tolls"

    def __str__(self):
        return f"Toll {self.vehicle.plate} - {self.date}"

class TuroTrip(models.Model):
    # Basic Info
    reservation_id = models.CharField(max_length=50, unique=True, verbose_name="Reservation ID")
    guest = models.CharField(max_length=255, verbose_name="Guest")
    vehicle_str = models.CharField(max_length=255, default='', verbose_name="Vehicle (Text)")
    vehicle_obj = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='trips', verbose_name="Linked Vehicle")
    period_obj = models.ForeignKey(Period, on_delete=models.SET_NULL, null=True, blank=True, related_name='trips', verbose_name="Linked Period")
    vehicle_name = models.CharField(max_length=255, verbose_name="Vehicle Name")
    vehicle_id = models.CharField(max_length=50, verbose_name="Vehicle ID")
    vin = models.CharField(max_length=50, verbose_name="VIN")
    plate_extracted = models.CharField(max_length=20, null=True, blank=True, verbose_name="Extracted Plate")
    
    # Dates
    start_date = models.DateTimeField(verbose_name="Trip Start")
    end_date = models.DateTimeField(verbose_name="Trip End")
    
    # Locations
    pickup_location = models.TextField(verbose_name="Pickup Location")
    return_location = models.TextField(verbose_name="Return Location")
    
    # Status
    trip_status = models.CharField(max_length=100, verbose_name="Trip Status")
    
    # Odometer and Distance
    check_in_odometer = models.IntegerField(null=True, blank=True, verbose_name="Check-in Odometer")
    check_out_odometer = models.IntegerField(null=True, blank=True, verbose_name="Check-out Odometer")
    distance_traveled = models.IntegerField(null=True, blank=True, verbose_name="Distance Traveled")
    
    # Earnings and Fees (DecimalFields for currency)
    trip_days = models.IntegerField(verbose_name="Trip Days")
    trip_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Trip Price")
    boost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Boost Price")
    
    # Discounts
    discount_3_day = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="3-Day Discount")
    discount_1_week = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="1-Week Discount")
    discount_2_week = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="2-Week Discount")
    discount_3_week = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="3-Week Discount")
    discount_1_month = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="1-Month Discount")
    discount_2_month = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="2-Month Discount")
    discount_3_month = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="3-Month Discount")
    discount_non_refundable = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Non-Refundable Discount")
    discount_early_bird = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Early Bird Discount")
    
    # Credits and Fees
    host_promotional_credit = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Host Promotional Credit")
    delivery = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Delivery")
    excess_distance = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Excess Distance")
    extras = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Extras")
    cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cancellation Fee")
    additional_usage = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Additional Usage")
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Late Fee")
    improper_return_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Improper Return Fee")
    airport_operations_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Airport Operations Fee")
    airport_parking_credit = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Airport Parking Credit")
    tolls_and_tickets = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Tolls and Tickets")
    on_trip_ev_charging = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="On-Trip EV Charging")
    post_trip_ev_charging = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Post-Trip EV Charging")
    smoking_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Smoking Fee")
    cleaning_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cleaning Fee")
    fines_paid_to_host = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Fines Paid to Host")
    gas_reimbursement = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Gas Reimbursement")
    gas_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Gas Fee")
    other_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Other Fees")
    sales_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Sales Tax")
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total Earnings")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Trip"
        verbose_name_plural = "Trips"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.reservation_id} - {self.vehicle_name} ({self.guest})"
