from django.core.management.base import BaseCommand
from accounts.scheduler import generate_bills
import time

class Command(BaseCommand):
    help = "Generate monthly/daily bills for tenants"

    def add_arguments(self, parser):
        parser.add_argument(
            '--test', action='store_true', help='Run in test mode (every 10s)'
        )

    def handle(self, *args, **options):
        test_mode = options.get('test', False)

        if test_mode:
            # Loop 6 times every 10 seconds (for testing)
            for _ in range(6):
                generate_bills()
                time.sleep(10)
            self.stdout.write(self.style.SUCCESS("Bills generated in test mode."))
        else:
            # Normal execution for production
            generate_bills()
            self.stdout.write(self.style.SUCCESS("Bills generated successfully."))
