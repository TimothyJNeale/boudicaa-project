# SDS 4.4 — Today views
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView

from ..forms import ActionForm
from ..models import Action
from .mixins import UserScopedMixin


class TodayView(LoginRequiredMixin, TemplateView):
    template_name = 'gtd/today/today.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()

        overdue = Action.objects.filter(user=user).overdue()

        days = []
        for offset in range(8):  # today + 7 days
            d = today + timedelta(days=offset)
            actions = Action.objects.filter(user=user).incomplete().for_date(d)
            if actions.exists() or d == today:
                days.append({'date': d, 'actions': actions})

        unscheduled_count = Action.objects.filter(user=user).unscheduled_standalone().count()
        next_scroll_date = today + timedelta(days=8)

        context.update({
            'overdue': overdue,
            'days': days,
            'unscheduled_count': unscheduled_count,
            'next_scroll_date': next_scroll_date,
        })
        return context


@login_required
def today_more(request: HttpRequest, date_str: str) -> HttpResponse:
    """Return the next batch of days for infinite scroll. SDS 4.4."""
    start_date = parse_date(date_str)
    user = request.user

    days = []
    for offset in range(7):
        d = start_date + timedelta(days=offset)
        actions = Action.objects.filter(user=user).incomplete().for_date(d)
        if actions.exists():
            days.append({'date': d, 'actions': actions})

    next_scroll_date = start_date + timedelta(days=7)

    return render(request, 'gtd/partials/today_day_sections.html', {
        'days': days,
        'next_scroll_date': next_scroll_date,
    })


# Alias for URL routing
TodayMoreView = today_more


class ActionSidePanelView(UserScopedMixin, DetailView):
    model = Action
    template_name = 'gtd/partials/action_side_panel.html'

    def get_template_names(self):
        return ['gtd/partials/action_side_panel.html']


class UnscheduledTasksView(LoginRequiredMixin, TemplateView):
    """SDS 3.4 — Unscheduled standalone tasks partial."""
    template_name = 'gtd/partials/unscheduled_tasks.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['actions'] = Action.objects.filter(
            user=self.request.user,
        ).unscheduled_standalone()
        return context


@login_required
@require_POST
def complete_action(request: HttpRequest, pk: int) -> HttpResponse:
    """Inline complete an action. SDS 4.4."""
    action = get_object_or_404(Action, pk=pk, user=request.user)
    action.complete()
    return render(request, 'gtd/partials/action_row_completed.html', {'action': action})


@login_required
@require_POST
def uncomplete_action(request: HttpRequest, pk: int) -> HttpResponse:
    """Undo action completion. SDS 3.4."""
    action = get_object_or_404(Action, pk=pk, user=request.user)
    action.ended_at = None
    action.save(update_fields=['ended_at', 'updated_at'])
    return render(request, 'gtd/partials/action_row.html', {'action': action})


@login_required
@require_POST
def update_action_from_panel(request: HttpRequest, pk: int) -> HttpResponse:
    """Save action from side panel. SDS 4.4."""
    action = get_object_or_404(Action, pk=pk, user=request.user)
    form = ActionForm(request.POST, instance=action, user=request.user)
    if form.is_valid():
        form.save()
    return render(request, 'gtd/partials/action_side_panel.html', {
        'action': action,
        'form': form,
    })
