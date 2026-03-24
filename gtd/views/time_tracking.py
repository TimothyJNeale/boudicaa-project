# SDS 4.6 — Time tracking views
from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from ..forms import WorkSessionForm
from ..models import Action, WorkSession
from .mixins import UserScopedMixin


class TimeDailyView(LoginRequiredMixin, TemplateView):
    template_name = 'gtd/time/daily.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        from django.utils.dateparse import parse_date
        date_str = self.kwargs.get('date')
        target_date = parse_date(date_str) if date_str else date.today()

        sessions = WorkSession.objects.filter(
            user=self.request.user,
        ).for_date(target_date).with_related()

        context.update({
            'target_date': target_date,
            'sessions': sessions,
        })
        return context


class WorkSessionListView(UserScopedMixin, ListView):
    model = WorkSession
    template_name = 'gtd/time/timecards.html'
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        return super().get_queryset().with_related()


class WorkSessionCreateView(LoginRequiredMixin, CreateView):
    model = WorkSession
    form_class = WorkSessionForm
    template_name = 'gtd/time/timecard_form.html'
    success_url = '/gtd/time/timecards/'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class WorkSessionUpdateView(UserScopedMixin, UpdateView):
    model = WorkSession
    form_class = WorkSessionForm
    template_name = 'gtd/time/timecard_form.html'
    success_url = '/gtd/time/timecards/'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


@login_required
@require_POST
def start_work_session(request: HttpRequest, action_id: int) -> HttpResponse:
    """Start a work session timer. SDS 3.5."""
    action = get_object_or_404(Action, pk=action_id, user=request.user)

    # Stop any active session first
    WorkSession.objects.filter(
        user=request.user, finished_at__isnull=True,
    ).update(finished_at=timezone.now())

    session = WorkSession.objects.create(
        action=action,
        user=request.user,
        started_at=timezone.now(),
    )

    return render(request, 'gtd/partials/running_timer.html', {'active_session': session})


@login_required
@require_POST
def stop_work_session(request: HttpRequest) -> HttpResponse:
    """Stop the active work session. SDS 3.5."""
    session = WorkSession.objects.filter(
        user=request.user, finished_at__isnull=True,
    ).first()
    if session:
        session.finish()

    return render(request, 'gtd/partials/running_timer.html', {'active_session': None})
