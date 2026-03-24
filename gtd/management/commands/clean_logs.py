# SDS 9.4 — Log cleanup management command
import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Clean old log files based on retention policy'

    def handle(self, *args, **options) -> None:
        log_dir = os.path.join(settings.BASE_DIR, 'logs')

        # Retention: 90 days for error logs, 30 days for warning logs
        retention = {
            'error': 90,
            'warning': 30,
        }

        now = time.time()
        cleaned = 0

        if not os.path.isdir(log_dir):
            self.stdout.write("No logs directory found.")
            return

        for filename in os.listdir(log_dir):
            filepath = os.path.join(log_dir, filename)
            if not os.path.isfile(filepath):
                continue

            file_age_days = (now - os.path.getmtime(filepath)) / 86400

            for log_type, max_days in retention.items():
                if log_type in filename and file_age_days > max_days:
                    os.remove(filepath)
                    cleaned += 1
                    self.stdout.write(f"Removed: {filename} (age: {file_age_days:.0f} days)")

        self.stdout.write(self.style.SUCCESS(f"Cleaned {cleaned} log files"))
