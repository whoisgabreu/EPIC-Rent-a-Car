import csv
from decimal import Decimal

def parse_decimal(value):
    if not value or value.strip() == "":
        return Decimal("0.00")
    clean_val = value.replace("$", "").replace(",", "").replace(" ", "").strip()
    try:
        if '(' in clean_val and ')' in clean_val: # Negative values in some CSVs are represented as (10.00)
             clean_val = "-" + clean_val.replace('(', '').replace(')', '')
        return Decimal(clean_val)
    except:
        return Decimal("0.00")

def analyze():
    f = open('trip_earnings_export_20260220.csv', 'r', encoding='utf-8-sig')
    reader = csv.DictReader(f)
    
    total_earnings_sum = Decimal("0.00")
    trip_price_sum = Decimal("0.00")
    boost_price_sum = Decimal("0.00")
    
    completed_count = 0
    
    # The 19 columns to subtract
    fields_to_subtract = [
        'Delivery', 'Excess distance', 'Extras', 'Cancellation fee', 
        'Additional usage', 'Late fee', 'Improper return fee', 
        'Airport operations fee', 'Airport parking credit', 'Tolls & tickets', 
        'On-trip EV charging', 'Post-trip EV charging', 'Smoking', 
        'Cleaning', 'Fines (paid to host)', 'Gas reimbursement', 
        'Gas fee', 'Other fees', 'Sales tax'
    ]
    
    subtractions_total = Decimal("0.00")
    
    for row in reader:
        # Clean row keys (Turo CSVs can have spaces or weird characters)
        clean_row = {k.strip(): v for k, v in row.items() if k}
        
        status = clean_row.get('Trip status', '').strip()
        if status == 'Completed':
            completed_count += 1
            te = parse_decimal(clean_row.get('Total earnings'))
            tp = parse_decimal(clean_row.get('Trip price'))
            bp = parse_decimal(clean_row.get('Boost price'))
            
            total_earnings_sum += te
            trip_price_sum += tp
            boost_price_sum += bp
            
            for field in fields_to_subtract:
                val = parse_decimal(clean_row.get(field))
                subtractions_total += val

    print(f"Completed Trips: {completed_count}")
    print(f"Total Earnings Sum (Completed): {total_earnings_sum}")
    print(f"Trip Price + Boost Price Sum (Completed): {trip_price_sum + boost_price_sum}")
    print(f"Subtractions Total: {subtractions_total}")
    print(f"Operational Result (Earnings - Subtractions): {total_earnings_sum - subtractions_total}")
    
    f.close()

if __name__ == '__main__':
    analyze()
