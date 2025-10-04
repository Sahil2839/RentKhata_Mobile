# accounts/management/commands/delete_old_mobile_bills.py

from django.core.management.base import BaseCommand
from accounts.models import Tenant, Billing

class Command(BaseCommand):
    help = "Delete old bills on mobile, keep only latest bill per tenant"

    def handle(self, *args, **kwargs):
        total_deleted = 0
        for tenant in Tenant.objects.all():
            bills = Billing.objects.filter(tenant=tenant).order_by('-created_at')
            if bills.count() > 1:
                bills_to_delete = bills[1:]
                deleted_count, _ = bills_to_delete.delete()
                total_deleted += deleted_count

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {total_deleted} old bills. Each tenant now has only 1 latest bill."
        ))
