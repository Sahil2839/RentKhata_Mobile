# accounts/management/commands/generate_bills.py
from django.core.management.base import BaseCommand
from accounts.scheduler import generate_bills  # import your function

class Command(BaseCommand):
    help = "Generate monthly/daily bills for tenants"

    def handle(self, *args, **options):
        generate_bills()
        self.stdout.write(self.style.SUCCESS("Bills generated successfully"))
