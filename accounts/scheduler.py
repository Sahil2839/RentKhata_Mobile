import calendar
from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from .models import OfflineTenants, LinkTenantLandlord, Billing

# --- Helper to add one month ---
def add_one_month(start_date):
    month = start_date.month
    year = start_date.year
    if month == 12:
        month = 1
        year += 1
    else:
        month += 1
    last_day_next_month = calendar.monthrange(year, month)[1]
    day = min(start_date.day, last_day_next_month)
    return date(year, month, day)

# --- Generate bills ---
def generate_bills():
    today = date.today()
    bills_created = 0

    # Combine tenants into a single list with type info
    tenants = [
        {"obj": t, "type": "offline"} for t in OfflineTenants.objects.all()
    ] + [
        {"obj": t, "type": "online"} for t in LinkTenantLandlord.objects.all()
    ]

    for t in tenants:
        tenant = t["obj"]
        tenant_type = t["type"]

        # Last bill
        if tenant_type == "offline":
            last_bill = tenant.offline_bill.order_by('-end_date').first()
        else:
            last_bill = tenant.online_bill.order_by('-end_date').first()

        # Tenant start date
        tenant_start_date = getattr(tenant, "start_date", date.today()) or date.today()

        # Determine next billing period
        if last_bill:
            next_start = last_bill.end_date + timedelta(days=1)
            next_end = add_one_month(next_start) - timedelta(days=1)
            previous_meter = last_bill.current_meter_reading or 0
            previous_due_amount = last_bill.remaining_due_amount or 0
        else:
            # For new tenants: always generate first bill
            next_start = tenant_start_date
            next_end = add_one_month(next_start) - timedelta(days=1)
            previous_meter = getattr(tenant, "starting_meter_reading", 0)
            previous_due_amount = getattr(tenant, "due_amount", 0)


        # Only create bill if today >= next_start
        if today >= next_start:
            # Check if a bill already exists for this period to avoid duplicates
            existing_bill = Billing.objects.filter(
                offline_tenant=tenant if tenant_type == "offline" else None,
                online_tenant=tenant if tenant_type == "online" else None,
                start_date=next_start,
                end_date=next_end
            ).first()

            if not existing_bill:
                Billing.objects.create(
                    offline_tenant=tenant if tenant_type == "offline" else None,
                    online_tenant=tenant if tenant_type == "online" else None,
                    rent=tenant.rent,
                    meter_rate=tenant.meter_rate or 10,
                    previous_meter_reading=previous_meter,
                    current_meter_reading=previous_meter,  # initial reading
                    previous_due_amount=previous_due_amount,
                    start_date=next_start,
                    end_date=next_end,
                )
                tenant_name = tenant.name if tenant_type == "offline" else tenant.tenant.full_name
                print(f"Bill created for {tenant_name} ({tenant_type}) from {next_start} to {next_end}")


# --- Start scheduler ---
def start_scheduler(test_mode=False):
    scheduler = BackgroundScheduler()
    interval_seconds = 10 if test_mode else 86400  # 1 day
    scheduler.add_job(generate_bills, 'interval', seconds=interval_seconds, id='generate_bills')
    scheduler.start()
    print(f"Scheduler started ({'test mode' if test_mode else 'daily mode'})")
