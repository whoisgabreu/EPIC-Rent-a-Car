"""
report_service.py
-----------------
Builds the full data context for the Investor Portfolio Performance PDF report.
All business logic lives here; the template stays logic-free.
"""

from decimal import Decimal
from django.db.models import Sum, Count, Min, Max
from django.utils import timezone
from datetime import date
import calendar

from dashboard.models import TuroTrip, Vehicle

# ── Constants ─────────────────────────────────────────────────────
INVESTOR_PROFIT_SHARE = Decimal('0.50')

DEDUCTION_FIELDS = [
    'delivery', 'excess_distance', 'extras', 'cancellation_fee',
    'additional_usage', 'late_fee', 'improper_return_fee',
    'airport_operations_fee', 'airport_parking_credit', 'tolls_and_tickets',
    'on_trip_ev_charging', 'post_trip_ev_charging', 'smoking_fee',
    'cleaning_fee', 'fines_paid_to_host', 'gas_reimbursement',
    'gas_fee', 'other_fees', 'sales_tax',
]


# ── Helpers ───────────────────────────────────────────────────────

def _d(val):
    return val if val is not None else Decimal('0.00')


def _deduction_sum(agg):
    return sum(_d(agg.get(f)) for f in DEDUCTION_FIELDS)


def _get_period(date_filter, date_from, date_to, base_qs):
    """Return (period_start, period_end) as date objects."""
    if date_from and date_to:
        return date_from, date_to

    if date_filter == 'current_month':
        now = timezone.now()
        last_day = calendar.monthrange(now.year, now.month)[1]
        return date(now.year, now.month, 1), date(now.year, now.month, last_day)

    # all_time → use min/max of actual trip data
    agg = base_qs.aggregate(mn=Min('start_date'), mx=Max('end_date'))
    if agg['mn'] and agg['mx']:
        return agg['mn'].date(), agg['mx'].date()
    today = date.today()
    return today, today


def _period_label(period_start, period_end):
    """Human-readable label like 'Q1 2026' or 'Jan 2025 – Mar 2026'."""
    if period_start.year == period_end.year:
        if period_start.month == period_end.month:
            return period_start.strftime('%B %Y')
        q = (period_start.month - 1) // 3 + 1
        q_end = (period_end.month - 1) // 3 + 1
        if q == q_end:
            return f'Q{q} {period_start.year}'
    return f'{period_start.strftime("%b %Y")} \u2013 {period_end.strftime("%b %Y")}'


def _short_name(name):
    """Shorten 'Mitsubishi Outlander 2022' → 'Outlander 2022'."""
    parts = name.strip().split()
    return ' '.join(parts[-2:]) if len(parts) >= 2 else name


# ── SVG Chart Generators ──────────────────────────────────────────

def _bar_svg(labels, values, colors, prefix='', suffix='', y_max=None):
    n = len(values)
    if n == 0:
        return '<svg width="100%" height="160"></svg>'

    W, H = 400, 160
    PL, PR, PT, PB = 52, 8, 12, 50
    cw = W - PL - PR
    ch = H - PT - PB

    raw_max = max(values) if values else 0
    scale = y_max if y_max is not None else (raw_max * 1.25 if raw_max > 0 else 100)
    if scale == 0:
        scale = 1

    bar_w = cw / n * 0.55
    bar_step = cw / n

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="100%" style="display:block;">'
    ]

    # Grid lines + Y labels
    for i in range(6):
        v = scale * i / 5
        y = PT + ch - (v / scale * ch)
        parts.append(
            f'<line x1="{PL}" y1="{y:.1f}" x2="{W-PR}" y2="{y:.1f}" '
            f'stroke="#E5E8EF" stroke-width="0.8"/>'
        )
        if prefix == '$':
            lbl = f'${int(v):,}' if v < 10000 else f'${int(v)//1000}k'
        else:
            lbl = f'{int(v)}{suffix}'
        parts.append(
            f'<text x="{PL-3}" y="{y+3:.1f}" text-anchor="end" '
            f'font-size="7.5" fill="#8892A4" font-family="Arial,sans-serif">{lbl}</text>'
        )

    # Bars + X labels
    for i, (lbl, val) in enumerate(zip(labels, values)):
        bh = max((val / scale) * ch, 0) if scale > 0 else 0
        bx = PL + i * bar_step + (bar_step - bar_w) / 2
        by = PT + ch - bh
        clr = colors[i] if isinstance(colors, list) else colors
        parts.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" '
            f'height="{bh:.1f}" fill="{clr}" rx="2"/>'
        )
        tx = bx + bar_w / 2
        ty = PT + ch + 6
        parts.append(
            f'<text transform="translate({tx:.1f},{ty}) rotate(-40)" '
            f'text-anchor="end" font-size="8" fill="#5A6478" '
            f'font-family="Arial,sans-serif">{lbl}</text>'
        )

    parts.append('</svg>')
    return ''.join(parts)


def _earnings_svg(vehicle_rows):
    labels = [_short_name(r['name']) for r in vehicle_rows]
    values = [float(r['net_earnings']) for r in vehicle_rows]
    colors = ['#4A6FA5'] * len(vehicle_rows)
    # Darken bars progressively for visual hierarchy
    shades = ['#2C5282', '#4A6FA5', '#5A85C5', '#6A9AD5', '#7AAAE5', '#8ABAF5']
    colors = [shades[i % len(shades)] for i in range(len(vehicle_rows))]
    return _bar_svg(labels, values, colors, prefix='$')


def _occupancy_svg(vehicle_rows):
    labels = [_short_name(r['name']) for r in vehicle_rows]
    values = [r['occupancy'] for r in vehicle_rows]
    colors = ['#27AE60' if v >= 75 else '#E74C3C' for v in values]
    return _bar_svg(labels, values, colors, suffix='%', y_max=100)


# ── Main Builder ──────────────────────────────────────────────────

def build_report_context(investor, date_filter='all_time', date_from=None, date_to=None):
    """
    Return a dict with all data needed by templates/reports/investor_report.html.

    Args:
        investor    – Investor model instance
        date_filter – 'all_time' | 'current_month'
        date_from   – optional date object (custom range start)
        date_to     – optional date object (custom range end)
    """

    vehicles = Vehicle.objects.filter(investor=investor)
    vehicle_count = vehicles.count()

    # Base queryset scoped to this investor + date range
    base_qs = TuroTrip.objects.filter(vehicle_obj__in=vehicles)

    if date_from and date_to:
        base_qs = base_qs.filter(
            start_date__date__gte=date_from,
            start_date__date__lte=date_to,
        )
    elif date_filter == 'current_month':
        now = timezone.now()
        base_qs = base_qs.filter(
            start_date__year=now.year,
            start_date__month=now.month,
        )

    period_start, period_end = _get_period(date_filter, date_from, date_to, base_qs)
    period_days = max((period_end - period_start).days + 1, 1)
    period_label = _period_label(period_start, period_end)

    # Split by status
    completed = base_qs.filter(trip_status='Completed')
    cancelled_total = base_qs.filter(trip_status='Cancelled').count()

    # Portfolio-level aggregate
    agg_kwargs = {
        'total_trips': Count('id'),
        'total_days': Sum('trip_days'),
        'total_earnings': Sum('total_earnings'),
        'total_miles': Sum('distance_traveled'),
    }
    for f in DEDUCTION_FIELDS:
        agg_kwargs[f] = Sum(f)

    p_agg = completed.aggregate(**agg_kwargs)

    total_gross = _d(p_agg['total_earnings'])
    total_deductions = _deduction_sum(p_agg)
    total_net = total_gross - total_deductions
    total_days = p_agg['total_days'] or 0
    total_trips = p_agg['total_trips'] or 0
    total_miles = p_agg['total_miles'] or 0
    investor_share = total_net * INVESTOR_PROFIT_SHARE
    avg_daily = (total_gross / total_days) if total_days > 0 else Decimal('0.00')

    # Fleet occupancy: total days rented / (period_days × number of vehicles)
    occ_denom = period_days * vehicle_count
    avg_occupancy = round((total_days / occ_denom * 100), 1) if occ_denom > 0 else 0.0

    # Per-vehicle rows
    vehicle_rows = []
    best_net_name, best_net_val = '', Decimal('-1')
    best_occ_name, best_occ_val = '', -1.0

    for v in vehicles:
        v_comp = completed.filter(vehicle_obj=v)
        v_canc = base_qs.filter(vehicle_obj=v, trip_status='Cancelled').count()

        va = v_comp.aggregate(
            count=Count('id'),
            days=Sum('trip_days'),
            earnings=Sum('total_earnings'),
            miles=Sum('distance_traveled'),
            **{f: Sum(f) for f in DEDUCTION_FIELDS},
        )

        v_trips = va['count'] or 0
        v_days = va['days'] or 0
        v_miles = va['miles'] or 0
        v_gross = _d(va['earnings'])
        v_deds = _deduction_sum(va)
        v_net = v_gross - v_deds
        v_share = v_net * INVESTOR_PROFIT_SHARE
        v_avg = (v_gross / v_days) if v_days > 0 else Decimal('0.00')
        v_occ = round((v_days / period_days * 100), 1) if period_days > 0 else 0.0

        row = {
            'name': v.year_make_model,
            'trips': v_trips,
            'cancellations': v_canc,
            'days': v_days,
            'miles': v_miles,
            'gross_price': v_gross,
            'deductions': v_deds,
            'net_earnings': v_net,
            'investor_share': v_share,
            'avg_daily': v_avg,
            'occupancy': v_occ,
        }
        vehicle_rows.append(row)

        if v_net > best_net_val:
            best_net_val, best_net_name = v_net, v.year_make_model
        if v_occ > best_occ_val:
            best_occ_val, best_occ_name = v_occ, v.year_make_model

    # Sort by net earnings descending (matching screenshot order)
    vehicle_rows.sort(key=lambda r: r['net_earnings'], reverse=True)

    return {
        'investor': investor,
        'period_start': period_start,
        'period_end': period_end,
        'period_label': period_label,
        'investor_share_pct': int(INVESTOR_PROFIT_SHARE * 100),
        'summary': {
            'total_vehicles': vehicle_count,
            'total_trips': total_trips,
            'total_cancellations': cancelled_total,
            'total_days': total_days,
            'total_miles': total_miles,
            'total_gross': total_gross,
            'total_deductions': total_deductions,
            'total_net': total_net,
            'investor_share': investor_share,
            'avg_occupancy': avg_occupancy,
            'avg_daily': avg_daily,
        },
        'vehicle_rows': vehicle_rows,
        'narrative': {
            'best_earnings_name': best_net_name,
            'best_earnings_val': best_net_val,
            'best_occupancy_name': best_occ_name,
            'best_occupancy_val': best_occ_val,
        },
        'earnings_svg': _earnings_svg(vehicle_rows),
        'occupancy_svg': _occupancy_svg(vehicle_rows),
    }
