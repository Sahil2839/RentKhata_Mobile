import os
import json
from django.core.management.base import BaseCommand
from accounts.models import CustomUser, LinkTenantLandlord, OfflineTenants, Billing

class Command(BaseCommand):
    help = "Export mobile data (all bills) to Downloads folder without deleting anything"

    def handle(self, *args, **kwargs):
        data = []

        # Iterate offline tenants
        for tenant in OfflineTenants.objects.all():
            bills = Billing.objects.filter(offline_tenant=tenant).order_by('-created_at')
            tenant_entry = {
                'tenant': {
                    'id': tenant.id,
                    'name': tenant.name,
                    'phone_number': tenant.phone_number,
                    'rent': tenant.rent,
                },
                'bills': [
                    {
                        'id': bill.id,
                        'rent': bill.rent,
                        'amount_paid': bill.amount_paid,
                        'remaining_due': bill.remaining_due_amount,
                        'start_date': str(bill.start_date),
                        'end_date': str(bill.end_date),
                    } for bill in bills
                ]
            }
            data.append(tenant_entry)

        # Output path to Termux Downloads
        downloads_path = '/storage/emulated/0/Download'
        os.makedirs(downloads_path, exist_ok=True)
        output_file = os.path.join(downloads_path, 'mobile_export.json')

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Exported {len(data)} tenants with all bills to {output_file}."
        ))
