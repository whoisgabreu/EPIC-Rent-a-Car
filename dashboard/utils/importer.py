import csv
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from ..models import TuroTrip

def parse_decimal(value):
    if not value or value.strip() == "":
        return Decimal("0.00")
    clean_val = value.replace("$", "").replace(",", "").replace(" ", "").strip()
    try:
        return Decimal(clean_val)
    except:
        return Decimal("0.00")

def parse_datetime(value):
    if not value or not isinstance(value, str) or value.strip() == "":
        return None
    # Possible formats: "2026-02-14 10:00 AM" or "2026-02-14 10:00:00"
    formats = ["%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except:
            continue
    return None

def parse_int(value):
    if not value or value.strip() == "":
        return None
    try:
        return int(value.strip())
    except:
        return None

def import_turo_csv(file_obj):
    if hasattr(file_obj, 'read'):
        content = file_obj.read().decode('utf-8').splitlines()
    else:
        with open(file_obj, 'r', encoding='utf-8') as f:
            content = f.readlines()
            
    if content:
        content[0] = content[0].lstrip('\ufeff')

    # Use skipinitialspace=True to handle "Guest", " Vehicle"
    reader = csv.DictReader(content, skipinitialspace=True)
    
    with transaction.atomic():
        # Step 1: Wipe all existing records as per new requirement
        TuroTrip.objects.all().delete()
        
        count = 0
        for row in reader:
            # Clean row keys: remove surrounding quotes and extra spaces
            clean_row = {k.strip().replace('"', ''): v for k, v in row.items() if k}
            
            trip_data = {
                'guest': clean_row.get('Guest', '').strip(),
                'vehicle': clean_row.get('Vehicle', '').strip(),
                'vehicle_name': clean_row.get('Vehicle name', '').strip(),
                'vehicle_id': clean_row.get('Vehicle id', '').strip(),
                'vin': clean_row.get('VIN', '').strip(),
                'start_date': parse_datetime(clean_row.get('Trip start')),
                'end_date': parse_datetime(clean_row.get('Trip end')),
                'pickup_location': clean_row.get('Pickup location', '').strip(),
                'return_location': clean_row.get('Return location', '').strip(),
                'trip_status': clean_row.get('Trip status', '').strip(),
                'check_in_odometer': parse_int(clean_row.get('Check-in odometer')),
                'check_out_odometer': parse_int(clean_row.get('Check-out odometer')),
                'distance_traveled': parse_int(clean_row.get('Distance traveled')),
                'trip_days': parse_int(clean_row.get('Trip days')) or 0,
                'trip_price': parse_decimal(clean_row.get('Trip price')),
                'boost_price': parse_decimal(clean_row.get('Boost price')),
                'discount_3_day': parse_decimal(clean_row.get('3-day discount')),
                'discount_1_week': parse_decimal(clean_row.get('1-week discount')),
                'discount_2_week': parse_decimal(clean_row.get('2-week discount')),
                'discount_3_week': parse_decimal(clean_row.get('3-week discount')),
                'discount_1_month': parse_decimal(clean_row.get('1-month discount')),
                'discount_2_month': parse_decimal(clean_row.get('2-month discount')),
                'discount_3_month': parse_decimal(clean_row.get('3-month discount')),
                'discount_non_refundable': parse_decimal(clean_row.get('Non-refundable discount')),
                'discount_early_bird': parse_decimal(clean_row.get('Early bird discount')),
                'host_promotional_credit': parse_decimal(clean_row.get('Host promotional credit')),
                'delivery': parse_decimal(clean_row.get('Delivery')),
                'excess_distance': parse_decimal(clean_row.get('Excess distance')),
                'extras': parse_decimal(clean_row.get('Extras')),
                'cancellation_fee': parse_decimal(clean_row.get('Cancellation fee')),
                'additional_usage': parse_decimal(clean_row.get('Additional usage')),
                'late_fee': parse_decimal(clean_row.get('Late fee')),
                'improper_return_fee': parse_decimal(clean_row.get('Improper return fee')),
                'airport_operations_fee': parse_decimal(clean_row.get('Airport operations fee')),
                'airport_parking_credit': parse_decimal(clean_row.get('Airport parking credit')),
                'tolls_and_tickets': parse_decimal(clean_row.get('Tolls & tickets')),
                'on_trip_ev_charging': parse_decimal(clean_row.get('On-trip EV charging')),
                'post_trip_ev_charging': parse_decimal(clean_row.get('Post-trip EV charging')),
                'smoking_fee': parse_decimal(clean_row.get('Smoking')),
                'cleaning_fee': parse_decimal(clean_row.get('Cleaning')),
                'fines_paid_to_host': parse_decimal(clean_row.get('Fines (paid to host)')),
                'gas_reimbursement': parse_decimal(clean_row.get('Gas reimbursement')),
                'gas_fee': parse_decimal(clean_row.get('Gas fee')),
                'other_fees': parse_decimal(clean_row.get('Other fees')),
                'sales_tax': parse_decimal(clean_row.get('Sales tax')),
                'total_earnings': parse_decimal(clean_row.get('Total earnings')),
            }
            
            reservation_id = clean_row.get('Reservation ID', '').strip()
            if reservation_id:
                if not trip_data['start_date'] or not trip_data['end_date']:
                    continue
                    
                TuroTrip.objects.create(
                    reservation_id=reservation_id,
                    **trip_data
                )
                count += 1
            
    return count
