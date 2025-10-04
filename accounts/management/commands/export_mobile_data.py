# accounts/management/commands/export_mobile_data.py

import os
import json
from django.core.management.base import BaseCommand
from accounts.models import Tenant, Billing

class Command(BaseCommand):
    help = "Export mobile data (all bills) without deleting anything"

    def handle(self, *args, **kwargs):
        data = []

        for tenant in Tenant.objects.all():
            bills = Billing.objects.filter(tenant=tenant).order_by('-created_at')
            
            tenant_entry = {
                'tenant': {
                    'id': tenant.id,
                    'name': tenant.name,
                    'phone_number': tenant.phone_number,
                    'rent': tenant.rent,
                    'role': getattr(tenant, 'role', None),
                    'extra_info': getattr(tenant, 'extra_info', None),
                },
                'bills': [
                    {
                        'id': bill.id,
                        'rent': bill.rent,
                        'amount_paid': bill.amount_paid,
                        'remaining_due': bill.remaining_due,
                        'start_date': str(bill.start_date),
                        'end_date': str(bill.end_date),
                    } for bill in bills
                ]
            }
            data.append(tenant_entry)

        output_file = os.path.join(os.getcwd(), 'mobile_export.json')
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Exported {len(data)} tenants with all bills to {output_file}."
        ))
