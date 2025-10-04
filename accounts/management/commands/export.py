import os
import json
from django.core.management.base import BaseCommand
from accounts.models import CustomUser, OfflineTenants, LinkTenantLandlord, Billing

class Command(BaseCommand):
    help = "Export mobile data: landlords, tenants (offline/online), links, and bills"

    def handle(self, *args, **kwargs):
        data = {
            "landlords": [],
            "online_tenants": [],
            "offline_tenants": [],
            "links": [],
            "bills": []
        }

        # ---------------- Landlords ----------------
        landlords = CustomUser.objects.filter(role='landlord')
        for l in landlords:
            data['landlords'].append({
                "id": l.id,
                "username": l.username,
                "phone": l.phone_number,
                "email": l.email
            })

        # ---------------- Online Tenants ----------------
        online_links = LinkTenantLandlord.objects.all()
        for link in online_links:
            tenant = link.tenant
            data['online_tenants'].append({
                "id": tenant.id,
                "username": tenant.username,
                "phone": tenant.phone_number,
                "linked_landlord_id": link.landlord.id
            })

        # ---------------- Offline Tenants ----------------
        offline_tenants = OfflineTenants.objects.all()
        for t in offline_tenants:
            data['offline_tenants'].append({
                "id": t.id,
                "name": t.name,
                "landlord_id": t.landlord.id,
                "phone": t.phone_number
            })

        # ---------------- Links ----------------
        for link in online_links:
            data['links'].append({
                "tenant_id": link.tenant.id,
                "landlord_id": link.landlord.id,
                "property_name": link.property_name,
                "rent": link.rent,
                "due_amount": link.due_amount,
                "meter_rate": link.meter_rate,
                "starting_meter_reading": link.starting_meter_reading,
                "start_date": str(link.start_date) if link.start_date else None,
                "end_date": str(link.end_date) if link.end_date else None,
            })

        # ---------------- Bills ----------------
        bills = Billing.objects.all()
        for b in bills:
            tenant_type = "offline" if b.offline_tenant else "online"
            tenant_id = b.offline_tenant.id if b.offline_tenant else b.online_tenant.tenant.id
            data['bills'].append({
                "tenant_type": tenant_type,
                "tenant_id": tenant_id,
                "rent": b.rent,
                "amount_paid": b.amount_paid,
                "previous_due": b.previous_due_amount,
                "start_date": str(b.start_date),
                "end_date": str(b.end_date),
                "current_meter_reading": b.current_meter_reading,
                "previous_meter_reading": b.previous_meter_reading,
                "meter_rate": b.meter_rate,
                "misc_charge": b.misc_charge,
                "misc_note": b.misc_note,
                "status": b.status,
            })

        # ---------------- Save JSON ----------------
        output_file = os.path.join(os.getcwd(), "mobile_export.json")
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f"Exported data to {output_file}"))
