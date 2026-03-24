# SDS 4.7 — Report views
import json
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F
from django.views.generic import TemplateView

from ..models import WorkSession
from ..utils import _bootstrap_to_hex


class DailyReportView(LoginRequiredMixin, TemplateView):
    template_name = 'gtd/time/reports/daily.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        offset = int(self.kwargs.get('day_offset', 0))
        target_date = date.today() - timedelta(days=offset)

        sessions = WorkSession.objects.filter(
            user=self.request.user,
        ).for_date(target_date).with_related()

        # Build chart data by project
        project_totals = {}
        for session in sessions:
            if not session.finished_at:
                continue
            name = session.action.project.name
            color = session.action.area.domain.color
            minutes = session.elapsed_minutes
            if name in project_totals:
                project_totals[name]['minutes'] += minutes
            else:
                project_totals[name] = {'minutes': minutes, 'color': color}

        chart_data = {
            'labels': list(project_totals.keys()),
            'data': [v['minutes'] for v in project_totals.values()],
            'colors': [_bootstrap_to_hex(v['color']) for v in project_totals.values()],
        }

        context.update({
            'target_date': target_date,
            'sessions': sessions,
            'chart_data': json.dumps(chart_data),
            'day_offset': offset,
        })
        return context


class WeeklyReportView(LoginRequiredMixin, TemplateView):
    template_name = 'gtd/time/reports/weekly.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        offset = int(self.kwargs.get('week_offset', 0))
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday()) - timedelta(weeks=offset)

        sessions = WorkSession.objects.filter(
            user=self.request.user,
        ).for_date_range(start_of_week, start_of_week + timedelta(days=6)).with_related()

        # Daily totals for the week
        daily_totals = {}
        for i in range(7):
            d = start_of_week + timedelta(days=i)
            daily_totals[d.strftime('%a')] = 0
        for session in sessions:
            if not session.finished_at:
                continue
            day_name = session.started_at.strftime('%a')
            daily_totals[day_name] = daily_totals.get(day_name, 0) + session.elapsed_minutes

        chart_data = {
            'labels': list(daily_totals.keys()),
            'data': list(daily_totals.values()),
        }

        context.update({
            'start_of_week': start_of_week,
            'sessions': sessions,
            'chart_data': json.dumps(chart_data),
            'week_offset': offset,
        })
        return context


class MonthlyByDayView(LoginRequiredMixin, TemplateView):
    template_name = 'gtd/time/reports/monthly_by_day.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        offset = int(self.kwargs.get('month_offset', 0))
        today = date.today()
        month = today.month - offset
        year = today.year
        while month <= 0:
            month += 12
            year -= 1

        sessions = WorkSession.objects.filter(
            user=self.request.user,
        ).for_month(year, month).with_related()

        context.update({
            'year': year,
            'month': month,
            'sessions': sessions,
            'month_offset': offset,
        })
        return context


class MonthlyByProjectView(LoginRequiredMixin, TemplateView):
    template_name = 'gtd/time/reports/monthly_by_project.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        offset = int(self.kwargs.get('month_offset', 0))
        today = date.today()
        month = today.month - offset
        year = today.year
        while month <= 0:
            month += 12
            year -= 1

        sessions = WorkSession.objects.filter(
            user=self.request.user,
        ).for_month(year, month).with_related()

        project_totals = {}
        for session in sessions:
            if not session.finished_at:
                continue
            name = session.action.project.name
            color = session.action.area.domain.color
            minutes = session.elapsed_minutes
            if name in project_totals:
                project_totals[name]['minutes'] += minutes
            else:
                project_totals[name] = {'minutes': minutes, 'color': color}

        chart_data = {
            'labels': list(project_totals.keys()),
            'data': [v['minutes'] for v in project_totals.values()],
            'colors': [_bootstrap_to_hex(v['color']) for v in project_totals.values()],
        }

        context.update({
            'year': year,
            'month': month,
            'sessions': sessions,
            'chart_data': json.dumps(chart_data),
            'month_offset': offset,
        })
        return context


class MonthlyByAreaView(LoginRequiredMixin, TemplateView):
    template_name = 'gtd/time/reports/monthly_by_area.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        offset = int(self.kwargs.get('month_offset', 0))
        today = date.today()
        month = today.month - offset
        year = today.year
        while month <= 0:
            month += 12
            year -= 1

        sessions = WorkSession.objects.filter(
            user=self.request.user,
        ).for_month(year, month).with_related()

        area_totals = {}
        for session in sessions:
            if not session.finished_at:
                continue
            area_name = f"{session.action.area.domain.name} / {session.action.area.name}"
            color = session.action.area.domain.color
            minutes = session.elapsed_minutes
            if area_name in area_totals:
                area_totals[area_name]['minutes'] += minutes
            else:
                area_totals[area_name] = {'minutes': minutes, 'color': color}

        chart_data = {
            'labels': list(area_totals.keys()),
            'data': [v['minutes'] for v in area_totals.values()],
            'colors': [_bootstrap_to_hex(v['color']) for v in area_totals.values()],
        }

        context.update({
            'year': year,
            'month': month,
            'sessions': sessions,
            'chart_data': json.dumps(chart_data),
            'month_offset': offset,
        })
        return context


class MonthlyByActionView(LoginRequiredMixin, TemplateView):
    template_name = 'gtd/time/reports/monthly_by_action.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        offset = int(self.kwargs.get('month_offset', 0))
        today = date.today()
        month = today.month - offset
        year = today.year
        while month <= 0:
            month += 12
            year -= 1

        sessions = WorkSession.objects.filter(
            user=self.request.user,
        ).for_month(year, month).with_related()

        action_totals = {}
        for session in sessions:
            if not session.finished_at:
                continue
            name = session.action.name
            minutes = session.elapsed_minutes
            if name in action_totals:
                action_totals[name] += minutes
            else:
                action_totals[name] = minutes

        chart_data = {
            'labels': list(action_totals.keys()),
            'data': list(action_totals.values()),
        }

        context.update({
            'year': year,
            'month': month,
            'sessions': sessions,
            'chart_data': json.dumps(chart_data),
            'month_offset': offset,
        })
        return context
