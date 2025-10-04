from django.core.management.base import BaseCommand
from accounts.models import Billing, OfflineTenants

class Command(BaseCommand):
    help = "Delete old bills on mobile, keep only latest bill per tenant"

    def handle(self, *args, **kwargs):
        total_deleted = 0

        for tenant in OfflineTenants.objects.all():
            bills = Billing.objects.filter(offline_tenant=tenant).order_by('-created_at')
            if bills.count() > 1:
                # Keep the latest, delete all others
                latest_bill = bills.first()
                bills_to_delete = bills.exclude(id=latest_bill.id)
                deleted_count, _ = bills_to_delete.delete()
                total_deleted += deleted_count

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {total_deleted} old bills. Each tenant now has only 1 latest bill."
            ))