# SDS 4.8 — Weekly review view and report generator
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Q, Sum
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from ..models import Action, InboxItem, Project, WorkSession


class WeeklyReviewView(LoginRequiredMixin, TemplateView):
    """SDS 4.8.1 — Interactive review screen."""
    template_name = 'gtd/review/review.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context.update({
            'inbox_count': InboxItem.objects.filter(
                user=user, processed_at__isnull=True,
            ).count(),
            'overdue_actions': Action.objects.filter(user=user).overdue(),
            'waiting_actions': Action.objects.filter(user=user).incomplete().filter(
                Q(waiting_on__isnull=False) | Q(is_skipped=True),
            ),
            'active_projects': Project.objects.filter(
                user=user, status__name__in=['IN ACTION', 'BACK BURNER'],
                is_protected=False,
            ).annotate(
                open_count=Count('action', filter=Q(action__ended_at__isnull=True)),
            ),
            'queued_projects': Project.objects.filter(
                user=user, status__name__in=['NEXT', 'WAITING', 'LONG'],
                is_protected=False,
            ),
            'someday_projects': Project.objects.filter(
                user=user, status__name__in=['PROPOSED', 'SOMEDAY'],
                is_protected=False,
            ),
            'unscheduled_tasks': Action.objects.filter(user=user).unscheduled_standalone(),
        })
        return context

    def post(self, request, *args, **kwargs):
        """Mark review as complete."""
        profile = getattr(request.user, 'userprofile', None)
        if profile:
            profile.last_review_date = date.today()
            profile.save(update_fields=['last_review_date'])
        return redirect('today')


class ReviewReportGenerator:
    """SDS 4.8.2 — Generate a structured weekly review report for a user."""

    def __init__(self, user):
        self.user = user
        self.generated_at = timezone.now()

    def generate(self) -> dict:
        """Return a structured report dict."""
        return {
            'generated_at': self.generated_at.isoformat(),
            'inbox': self._inbox_summary(),
            'overdue': self._overdue_summary(),
            'stalled_projects': self._stalled_projects(),
            'empty_next_actions': self._projects_without_next_actions(),
            'waiting_for': self._waiting_for_summary(),
            'someday_review': self._someday_review(),
            'time_summary': self._time_summary(),
            'highlights': self._highlights(),
        }

    def _inbox_summary(self) -> dict:
        """Unprocessed inbox items — count and age of oldest."""
        items = InboxItem.objects.filter(user=self.user, processed_at__isnull=True)
        oldest = items.order_by('created_at').first()
        return {
            'count': items.count(),
            'oldest_days': (self.generated_at.date() - oldest.created_at.date()).days if oldest else 0,
        }

    def _overdue_summary(self) -> list:
        """Actions past their scheduled end date."""
        return list(Action.objects.filter(user=self.user).overdue().values(
            'id', 'name', 'scheduled_end', 'project__name',
        ))

    def _stalled_projects(self) -> list:
        """Active projects with no action activity in 14+ days."""
        cutoff = self.generated_at - timedelta(days=14)
        active = Project.objects.filter(
            user=self.user, status__name__in=['IN ACTION', 'BACK BURNER'],
            is_protected=False,
        )
        stalled = []
        for project in active:
            latest_action = project.action_set.order_by('-updated_at').first()
            if not latest_action or latest_action.updated_at < cutoff:
                stalled.append({
                    'id': project.id,
                    'name': project.name,
                    'days_inactive': (
                        self.generated_at.date() - (
                            latest_action.updated_at.date() if latest_action
                            else project.created_at.date()
                        )
                    ).days,
                })
        return stalled

    def _projects_without_next_actions(self) -> list:
        """Active projects with zero open actions."""
        return list(Project.objects.filter(
            user=self.user, status__name__in=['IN ACTION'], is_protected=False,
        ).annotate(
            open_count=Count('action', filter=Q(action__ended_at__isnull=True)),
        ).filter(open_count=0).values('id', 'name'))

    def _waiting_for_summary(self) -> list:
        """Actions in waiting/delegated state."""
        return list(Action.objects.filter(
            user=self.user, ended_at__isnull=True,
        ).filter(
            Q(waiting_on__isnull=False) | Q(is_skipped=True),
        ).values('id', 'name', 'waiting_on', 'project__name'))

    def _someday_review(self) -> list:
        """Someday/maybe items that haven't been reviewed in 30+ days."""
        cutoff = self.generated_at - timedelta(days=30)
        return list(Project.objects.filter(
            user=self.user, status__name__in=['PROPOSED', 'SOMEDAY'],
            is_protected=False, updated_at__lt=cutoff,
        ).values('id', 'name').order_by('-updated_at'))

    def _time_summary(self) -> dict:
        """Time tracked this week vs last week."""
        today = self.generated_at.date()
        week_start = today - timedelta(days=today.weekday())
        last_week_start = week_start - timedelta(days=7)

        this_week = WorkSession.objects.filter(
            user=self.user, started_at__date__gte=week_start,
        ).aggregate(
            total=Sum(F('finished_at') - F('started_at')),
        )['total'] or timedelta()

        last_week = WorkSession.objects.filter(
            user=self.user, started_at__date__gte=last_week_start,
            started_at__date__lt=week_start,
        ).aggregate(
            total=Sum(F('finished_at') - F('started_at')),
        )['total'] or timedelta()

        return {
            'this_week_hours': round(this_week.total_seconds() / 3600, 1),
            'last_week_hours': round(last_week.total_seconds() / 3600, 1),
        }

    def _highlights(self) -> list:
        """Actions completed this week."""
        today = self.generated_at.date()
        week_start = today - timedelta(days=today.weekday())
        return list(Action.objects.filter(
            user=self.user, ended_at__date__gte=week_start,
        ).values('id', 'name', 'project__name', 'ended_at'))
