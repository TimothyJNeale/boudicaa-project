import os
import sys

from django.apps import AppConfig


class GtdConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gtd'
    verbose_name = 'Boudicaa'

    def ready(self) -> None:
        import gtd.signals  # noqa: F401

        # Only show startup info for runserver / wsgi, not migrations or tests
        if 'runserver' not in sys.argv and 'gunicorn' not in sys.argv[0:1]:
            return

        # Avoid printing twice — Django runserver spawns a reloader process
        if os.environ.get('RUN_MAIN') != 'true':
            return

        from django.conf import settings
        from .version import __version__

        db_engine = settings.DATABASES['default']['ENGINE'].split('.')[-1]
        db_name = settings.DATABASES['default'].get('NAME', '')

        print()
        print('=' * 60)
        print(f'  Boudicaa v{__version__}')
        print('=' * 60)
        print(f'  DEBUG:          {settings.DEBUG}')
        print(f'  Database:       {db_engine} ({db_name})')
        print(f'  Allowed hosts:  {", ".join(settings.ALLOWED_HOSTS)}')
        print(f'  Protected mode: {settings.PROTECTED_MODE}')
        print(f'  Email backend:  {settings.EMAIL_BACKEND.split(".")[-1]}')
        print('=' * 60)
        print()

        # Defer seed data check until after Django is fully initialised
        from django.core.signals import request_started
        request_started.connect(self._check_seed_data_once, weak=False)

    @classmethod
    def _check_seed_data_once(cls, **kwargs) -> None:
        """Check seed data on first request, then disconnect."""
        from django.core.signals import request_started
        request_started.disconnect(cls._check_seed_data_once)

        cls._check_seed_data()

    @staticmethod
    def _check_seed_data() -> None:
        """Check that required seed data exists and warn if missing."""
        from django.db import connection

        # Skip if tables don't exist yet (pre-migration)
        table_names = connection.introspection.table_names()
        if 'gtd_status' not in table_names:
            print()
            print('  WARNING: Database tables not created yet.')
            print('  Run: python manage.py migrate')
            print()
            return

        from .models import Area, Context, Domain, Priority, Status

        issues = []

        status_count = Status.objects.count()
        if status_count == 0:
            issues.append('No statuses found (expected 11)')
        elif status_count < 11:
            issues.append(f'Only {status_count}/11 statuses found')

        priority_count = Priority.objects.count()
        if priority_count == 0:
            issues.append('No priorities found (expected 5)')
        elif priority_count < 5:
            issues.append(f'Only {priority_count}/5 priorities found')

        if not Domain.objects.system_defaults().exists():
            issues.append('No system default domain found')

        if not Area.objects.filter(user__isnull=True).exists():
            issues.append('No system default area found')

        if not Context.objects.system_defaults().exists():
            issues.append('No system default context found')

        if issues:
            print()
            print('  *** SEED DATA MISSING ***')
            for issue in issues:
                print(f'  - {issue}')
            print()
            print('  Run: python manage.py loaddata gtd/fixtures/seed_data.json')
            print()
