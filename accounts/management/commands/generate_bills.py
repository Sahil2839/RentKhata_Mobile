from django.core.management.base import BaseCommand
from accounts.scheduler import generate_bills

class Command(BaseCommand):
    help = "Generate bills manually"

    def handle(self, *args, **options):
        generate_bills()
        self.stdout.write(self.style.SUCCESS("Bills generated successfully"))
