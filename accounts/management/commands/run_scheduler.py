from django.core.management.base import BaseCommand
from accounts.scheduler import start_scheduler

class Command(BaseCommand):
    help = "Start APScheduler for billing"

    def add_arguments(self, parser):
        parser.add_argument(
            '--test', action='store_true', help='Run scheduler in test mode (every 10s)'
        )

    def handle(self, *args, **options):
        test_mode = options.get('test', False)
        start_scheduler(test_mode=test_mode)
        print(f"Scheduler is running in {'test' if test_mode else 'daily'} mode. Press Ctrl+C to exit.")

        import time
        try:
            while True:
                time.sleep(2)
        except KeyboardInterrupt:
            print("Scheduler stopped.")
