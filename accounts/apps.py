from django.apps import AppConfig
import threading
import time
import datetime
import os

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from .scheduler import generate_bills

        def run_bills():
            test_mode = os.environ.get("BILL_TEST_MODE", "0") == "1"

            while True:
                now = datetime.datetime.now()
                print(f"[{now}] Running generate_bills...")
                try:
                    generate_bills()
                except Exception as e:
                    print(f"[{now}] Error: {e}")

                if test_mode:
                    time.sleep(10)  # every 10 seconds
                else:
                    # Sleep until next day at 00:01
                    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
                    next_run = datetime.datetime.combine(tomorrow, datetime.time(hour=0, minute=1))
                    seconds_to_sleep = (next_run - datetime.datetime.now()).total_seconds()
                    time.sleep(max(seconds_to_sleep, 0))

        # Prevent multiple threads on dev reload
        if not hasattr(self, 'bills_thread_started'):
            thread = threading.Thread(target=run_bills, daemon=True)
            thread.start()
            self.bills_thread_started = True
