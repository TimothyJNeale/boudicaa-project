# SDS 2.10 — WorkSession model
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class WorkSessionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(finished_at__isnull=True)

    def completed(self):
        return self.filter(finished_at__isnull=False)

    def for_user(self, user):
        return self.filter(user=user)

    def for_action(self, action):
        return self.filter(action=action)

    def for_date(self, date):
        from datetime import datetime, time
        start = timezone.make_aware(datetime.combine(date, time.min))
        end = timezone.make_aware(datetime.combine(date, time.max))
        return self.filter(started_at__range=(start, end))

    def for_week(self, year: int, week: int):
        from datetime import date
        start = date.fromisocalendar(year, week, 1)
        end = date.fromisocalendar(year, week, 7)
        return self.filter(started_at__date__range=(start, end))

    def for_month(self, year: int, month: int):
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        from datetime import date
        start = date(year, month, 1)
        end = date(year, month, last_day)
        return self.filter(started_at__date__range=(start, end))

    def for_date_range(self, start, end):
        return self.filter(started_at__date__range=(start, end))

    def with_related(self):
        return self.select_related(
            'action', 'action__project', 'action__area', 'action__area__domain',
        )


class WorkSession(models.Model):
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    action = models.ForeignKey('gtd.Action', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = WorkSessionQuerySet.as_manager()

    class Meta:
        db_table = 'gtd_cards'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'started_at']),
            models.Index(fields=['user', 'finished_at']),
        ]

    def __str__(self) -> str:
        return f"Session: {self.action.name} ({self.started_at})"

    @property
    def is_active(self) -> bool:
        return self.finished_at is None

    @property
    def elapsed_time(self) -> timedelta:
        end = self.finished_at or timezone.now()
        return end - self.started_at

    @property
    def elapsed_time_formatted(self) -> str:
        total_seconds = int(self.elapsed_time.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @property
    def elapsed_minutes(self) -> int:
        return int(self.elapsed_time.total_seconds() / 60)

    def finish(self, finish_time=None) -> None:
        self.finished_at = finish_time or timezone.now()
        self.save(update_fields=['finished_at'])
