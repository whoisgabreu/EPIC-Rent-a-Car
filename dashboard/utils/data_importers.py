import csv
import os
from decimal import Decimal
from datetime import datetime
from django.contrib.auth.models import User
from django.db import transaction
from ..models import Investor, Vehicle, Period, Investment, Expense, Toll

def parse_decimal(value):
    if not value or value.strip() == "":
        return Decimal("0.00")
    # Handle both $1,234.56 and $1.234,56 (if any)
    clean_val = value.replace("$", "").replace(" ", "").strip()
    # Assume US format (dot for decimal) but handle comma as thousand separator
    if "," in clean_val and "." in clean_val:
        clean_val = clean_val.replace(",", "")
    elif "," in clean_val:
        # If only comma, it might be decimal separator or thousand separator
        # In this context, it's likely decimal if it's like "1,00"
        if len(clean_val.split(",")[-1]) == 2:
            clean_val = clean_val.replace(",", ".")
        else:
            clean_val = clean_val.replace(",", "")
            
    try:
        return Decimal(clean_val)
    except:
        return Decimal("0.00")

def parse_date(value):
    if not value or value.strip() == "":
        return None
    val = value.strip()
    
    # Handle "17 de Janeiro de 2026"
    months_pt = {
        'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4,
        'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8,
        'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12
    }
    for mon_name, mon_num in months_pt.items():
        if mon_name in val:
            try:
                # "17 de Janeiro de 2026" -> "17 1 2026"
                parts = val.split(' de ')
                day = int(parts[0])
                year = int(parts[2])
                return datetime(year, mon_num, day).date()
            except:
                pass

    formats = ["%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(val, fmt).date()
        except:
            continue
    return None

def get_delimiter(file_path):
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        if '\t' in first_line: return '\t'
        if ';' in first_line: return ';'
        return ','

def import_periods(periods_csv_path):
    with transaction.atomic():
        with open(periods_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=get_delimiter(periods_csv_path), skipinitialspace=True)
            for row in reader:
                Period.objects.update_or_create(
                    period_key=row.get('period', '').strip(),
                    defaults={
                        'start_date': parse_date(row.get('start_date')),
                        'end_date': parse_date(row.get('end_date')),
                    }
                )

def import_investments(investments_csv_path):
    with transaction.atomic():
        with open(investments_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=get_delimiter(investments_csv_path), skipinitialspace=True)
            for row in reader:
                investor_name = row.get('investor', '').strip()
                vin = row.get('vehicle', '').strip()
                if not investor_name or not vin: continue
                
                investor, _ = Investor.objects.get_or_create(name=investor_name)
                vehicle, _ = Vehicle.objects.get_or_create(vin=vin, defaults={'investor': investor})
                
                # Update total invested for investor
                amount = parse_decimal(row.get('invested_amount'))
                
                investment, created = Investment.objects.update_or_create(
                    name=row.get('name', '').strip(),
                    investor=investor,
                    vehicle=vehicle,
                    defaults={
                        'ownership_percentage': parse_decimal(row.get('ownership(%)')),
                        'invested_amount': amount,
                        'start_date': parse_date(row.get('start_date')),
                        'duration_days': int(row.get('investment_duration(days)') or 0),
                    }
                )

def import_tolls(tolls_csv_path):
    with transaction.atomic():
        # Handle the weird toll CSV where header has ; but rows have tabs
        with open(tolls_csv_path, 'r', encoding='utf-8-sig') as f:
            header = f.readline().strip().split(';')
            if len(header) < 2: # Try tab
                f.seek(0)
                header = f.readline().strip().split('\t')
            
            # Read remainder of file
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < len(header):
                    parts = line.strip().split(';')
                if len(parts) < 2: continue
                
                row = dict(zip(header, parts))
                vin = row.get('vin_text', '').strip()
                if not vin: continue
                
                vehicle = Vehicle.objects.filter(vin=vin).first()
                if not vehicle: continue
                
                period_key = row.get('period', '').strip()
                period = Period.objects.filter(period_key=period_key).first()
                
                Toll.objects.create(
                    vehicle=vehicle,
                    period=period,
                    plate=row.get('plate', '').strip(),
                    amount=parse_decimal(row.get('amount')),
                    date=parse_date(row.get('month')) or datetime.now().date()
                )

def import_expenses(expenses_csv_path):
    with transaction.atomic():
        with open(expenses_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=get_delimiter(expenses_csv_path), skipinitialspace=True)
            for row in reader:
                vin = row.get('vin_text', '').strip()
                if not vin: continue
                
                vehicle = Vehicle.objects.filter(vin=vin).first()
                if not vehicle: continue
                
                period_key = row.get('period', '').strip()
                period = Period.objects.filter(period_key=period_key).first()
                
                Expense.objects.create(
                    name=row.get('expense_name', '').strip(),
                    vehicle=vehicle,
                    period=period,
                    expense_type=row.get('expense_type', 'Other'),
                    date=parse_date(row.get('date_incurred')) or datetime.now().date(),
                    amount=parse_decimal(row.get('amount')),
                    description=row.get('description', ''),
                    status=row.get('approved_status', 'Approved'),
                    payment_status=row.get('payment_status', 'Paid')
                )

def import_investors_and_users(users_csv_path, investors_csv_path):
    """
    Import users and link them to investors.
    """
    with transaction.atomic():
        # Step 1: Create Users from uers.csv
        with open(users_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';', skipinitialspace=True)
            for row in reader:
                email = row.get('email', '').strip()
                name = row.get('investor_name', '').strip()
                role = row.get('role', '').strip()
                
                if not email: continue
                
                user, created = User.objects.get_or_create(username=email, defaults={'email': email})
                if created:
                    user.set_password("EPIC2026!") # Default password
                    if role == 'Admin':
                        user.is_staff = True
                        user.is_superuser = True
                    user.save()
                
                # Create/Update Investor profile
                investor, _ = Investor.objects.get_or_create(name=name)
                investor.user = user
                investor.save()

def import_vehicles(vehicles_csv_path):
    """
    Import vehicles from vehicles.csv
    """
    with transaction.atomic():
        with open(vehicles_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';', skipinitialspace=True)
            for row in reader:
                vin = row.get('vin', '').strip()
                if not vin:
                    continue
                
                investor_name = row.get('investor', '').strip()
                investor, _ = Investor.objects.get_or_create(name=investor_name)
                
                Vehicle.objects.update_or_create(
                    vin=vin,
                    defaults={
                        'plate': row.get('plate', '').strip(),
                        'year_make_model': row.get('year/make/model', '').strip(),
                        'investor': investor,
                        'status': row.get('in_service_status', '').strip() or 'Active',
                        'acquisition_date': parse_date(row.get('acquisition_date')),
                    }
                )

def run_all_imports(base_path):
    users_path = os.path.join(base_path, 'users.csv') # Fixed name
    investors_path = os.path.join(base_path, 'investors.csv')
    vehicles_path = os.path.join(base_path, 'vehicles.csv')
    periods_path = os.path.join(base_path, 'periods.csv')
    investments_path = os.path.join(base_path, 'investments.csv')
    tolls_path = os.path.join(base_path, 'tolls.csv')
    expenses_path = os.path.join(base_path, 'costs_and_expenses.csv')
    
    import_investors_and_users(users_path, investors_path)
    import_vehicles(vehicles_path)
    import_periods(periods_path)
    import_investments(investments_path)
    # Clear old tolls/expenses before re-importing if desired, 
    # but for now we'll just append (Caution: might duplicate if run multiple times)
    Toll.objects.all().delete()
    Expense.objects.all().delete()
    import_tolls(tolls_path)
    import_expenses(expenses_path)
    
    return "Import successful"
