import os
import json
from django.core.management.base import BaseCommand
from accounts.models import OfflineTenants, LinkTenantLandlord, Billing, CustomUser

class Command(BaseCommand):
    help = "Export mobile data (all bills) without deleting anything"

    def handle(self, *args, **kwargs):
        data = []

        # ------------------ Offline Tenants ------------------
        for tenant in OfflineTenants.objects.all():
            bills = Billing.objects.filter(offline_tenant=tenant).order_by('-created_at')

            tenant_entry = {
                'tenant_type': 'offline',
                'tenant': {
                    'id': tenant.id,
                    'name': tenant.name,
                    'phone_number': tenant.phone_number,
                    'rent': tenant.rent,
                    'property_name': tenant.property_name,
                },
                'bills': [
                    {
                        'id': bill.id,
                        'rent': bill.rent,
                        'amount_paid': bill.amount_paid,
                        'remaining_due': bill.remaining_due_amount,
                        'start_date': str(bill.start_date),
                        'end_date': str(bill.end_date),
                        'previous_due': bill.previous_due_amount,
                        'meter_rate': bill.meter_rate,
                        'current_meter_reading': bill.current_meter_reading,
                        'previous_meter_reading': bill.previous_meter_reading,
                        'misc_charge': bill.misc_charge,
                        'misc_note': bill.misc_note,
                        'status': bill.status,
                    } for bill in bills
                ]
            }
            data.append(tenant_entry)

        # ------------------ Online Tenants (via LinkTenantLandlord) ------------------
        for link in LinkTenantLandlord.objects.all():
            bills = Billing.objects.filter(online_tenant=link).order_by('-created_at')

            tenant_entry = {
                'tenant_type': 'online',
                'tenant': {
                    'id': link.id,
                    'tenant_username': link.tenant.username,
                    'landlord_username': link.landlord.username,
                    'rent': link.rent,
                    'property_name': link.property_name,
                },
                'bills': [
                    {
                        'id': bill.id,
                        'rent': bill.rent,
                        'amount_paid': bill.amount_paid,
                        'remaining_due': bill.remaining_due_amount,
                        'start_date': str(bill.start_date),
                        'end_date': str(bill.end_date),
                        'previous_due': bill.previous_due_amount,
                        'meter_rate': bill.meter_rate,
                        'current_meter_reading': bill.current_meter_reading,
                        'previous_meter_reading': bill.previous_meter_reading,
                        'misc_charge': bill.misc_charge,
                        'misc_note': bill.misc_note,
                        'status': bill.status,
                    } for bill in bills
                ]
            }
            data.append(tenant_entry)

        # ------------------ Save to JSON ------------------
        output_file = os.path.join(os.getcwd(), 'mobile_export.json')
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Exported {len(data)} tenants with all bills to {output_file}."
        ))
