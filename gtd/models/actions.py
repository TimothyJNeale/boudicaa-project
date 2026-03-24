# SDS 2.8, 2.9 — Action, InboxItem
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class ActionQuerySet(models.QuerySet):
    def incomplete(self):
        return self.filter(ended_at__isnull=True)

    def complete(self):
        return self.filter(ended_at__isnull=False)

    def overdue(self):
        return self.filter(
            scheduled_end__lt=timezone.now(),
            ended_at__isnull=True,
        )

    def today(self):
        from datetime import date
        today = date.today()
        return self.for_date(today)

    def for_date(self, date):
        from datetime import datetime, time
        start = timezone.make_aware(datetime.combine(date, time.min))
        end = timezone.make_aware(datetime.combine(date, time.max))
        return self.filter(
            models.Q(scheduled_start__range=(start, end))
            | models.Q(scheduled_end__range=(start, end))
        )

    def for_date_range(self, start, end):
        return self.filter(
            models.Q(scheduled_start__date__range=(start, end))
            | models.Q(scheduled_end__date__range=(start, end))
        )

    def unscheduled_standalone(self):
        return self.filter(
            project__is_protected=True,
            scheduled_start__isnull=True,
            scheduled_end__isnull=True,
            ended_at__isnull=True,
        )

    def next_actions(self):
        return self.filter(
            ended_at__isnull=True,
            is_skipped=False,
            waiting_on__isnull=True,
        )

    def scheduled_between(self, start, end):
        return self.filter(scheduled_start__range=(start, end))


class Action(models.Model):
    name = models.CharField(max_length=70)
    notes = models.TextField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=99999)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    waiting_on = models.PositiveIntegerField(null=True, blank=True)
    time_budgeted = models.PositiveIntegerField(null=True, blank=True)
    is_skipped = models.BooleanField(default=False)
    project = models.ForeignKey('gtd.Project', on_delete=models.CASCADE)
    area = models.ForeignKey('gtd.Area', on_delete=models.PROTECT)
    priority = models.ForeignKey('gtd.Priority', on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    context = models.ForeignKey(
        'gtd.Context', on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # v3 NEW — recurrence
    recurrence_rule = models.CharField(max_length=255, null=True, blank=True)
    recurrence_end = models.DateField(null=True, blank=True)

    objects = ActionQuerySet.as_manager()

    class Meta:
        db_table = 'gtd_actions'
        ordering = ['scheduled_start', 'priority__rank', 'name']
        indexes = [
            models.Index(fields=['user', 'ended_at']),
            models.Index(fields=['user', 'scheduled_start']),
            models.Index(fields=['user', 'scheduled_end']),
            models.Index(fields=['project', 'display_order']),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_complete(self) -> bool:
        return self.ended_at is not None

    @property
    def is_overdue(self) -> bool:
        return (
            self.scheduled_end is not None
            and self.scheduled_end < timezone.now()
            and not self.is_complete
        )

    @property
    def is_waiting(self) -> bool:
        return self.waiting_on is not None

    @property
    def is_actionable(self) -> bool:
        return not self.is_complete and not self.is_skipped and not self.is_waiting

    @property
    def is_recurring(self) -> bool:
        return self.recurrence_rule is not None

    @property
    def total_time_worked(self) -> timedelta:
        total = timedelta()
        for session in self.worksession_set.filter(finished_at__isnull=False):
            total += session.finished_at - session.started_at
        return total

    def complete(self) -> None:
        self.ended_at = timezone.now()
        self.save(update_fields=['ended_at', 'updated_at'])
        if self.is_recurring:
            self.generate_next_occurrence()

    def skip(self) -> None:
        self.is_skipped = True
        self.save(update_fields=['is_skipped', 'updated_at'])
        if self.is_recurring:
            self.generate_next_occurrence()

    def generate_next_occurrence(self):
        """Create the next instance of a recurring action. SDS 2.8."""
        if not self.recurrence_rule:
            return None

        from dateutil.rrule import rrulestr

        rule = rrulestr(self.recurrence_rule, dtstart=self.scheduled_start)
        next_dates = list(rule.between(
            self.scheduled_start,
            self.scheduled_start + timedelta(days=365),
            inc=False,
        ))

        if not next_dates:
            return None

        next_date = next_dates[0]

        if self.recurrence_end and next_date.date() > self.recurrence_end:
            return None

        duration = None
        if self.scheduled_start and self.scheduled_end:
            duration = self.scheduled_end - self.scheduled_start

        new_action = Action(
            name=self.name,
            notes=self.notes,
            display_order=self.display_order,
            scheduled_start=next_date,
            scheduled_end=next_date + duration if duration else None,
            time_budgeted=self.time_budgeted,
            project=self.project,
            area=self.area,
            priority=self.priority,
            user=self.user,
            context=self.context,
            recurrence_rule=self.recurrence_rule,
            recurrence_end=self.recurrence_end,
        )
        new_action.save()
        return new_action


class InboxItem(models.Model):
    item = models.TextField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_note = models.CharField(max_length=255, null=True, blank=True)
    area = models.ForeignKey(
        'gtd.Area', on_delete=models.SET_NULL, null=True, blank=True,
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gtd_stuff'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'processed_at']),
        ]

    def __str__(self) -> str:
        return self.item[:50] if self.item else f"InboxItem {self.pk}"

    @property
    def is_processed(self) -> bool:
        return self.processed_at is not None

    def mark_processed(self, note: str = '') -> None:
        self.processed_at = timezone.now()
        self.processing_note = note
        self.save(update_fields=['processed_at', 'processing_note'])
