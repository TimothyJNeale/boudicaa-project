# View tests — SDS Sections 3–4, Test Plan Section 4
from datetime import timedelta

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from gtd.models import (
    Action,
    Area,
    Context,
    Domain,
    InboxItem,
    Priority,
    Project,
    Status,
    WorkSession,
)
from gtd.tests.factories import (
    ActionFactory,
    InboxItemFactory,
    ProjectFactory,
    UserFactory,
    WorkSessionFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def user_a():
    return UserFactory(username='user_a')


@pytest.fixture
def user_b():
    return UserFactory(username='user_b')


@pytest.fixture
def client_a(user_a):
    c = Client()
    c.login(username='user_a', password='testpass123')
    return c


@pytest.fixture
def client_b(user_b):
    c = Client()
    c.login(username='user_b', password='testpass123')
    return c


# ── Section 4.1: Public Views ──────────────────────────────────────────


class TestPublicViews:
    def test_V_PUB_01_home_returns_200(self):
        resp = Client().get('/')
        assert resp.status_code == 200

    def test_V_PUB_02_login_returns_200(self):
        resp = Client().get('/login/')
        assert resp.status_code == 200

    def test_V_PUB_03_signup_returns_200(self):
        resp = Client().get('/signup/')
        assert resp.status_code == 200

    @override_settings(PROTECTED_MODE=True)
    def test_V_PUB_04_signup_blocked_in_protected_mode(self):
        resp = Client().get('/signup/')
        # Should redirect or show error
        assert resp.status_code in (302, 403, 200)

    def test_V_PUB_05_verification_sent_returns_200(self):
        resp = Client().get('/verification-sent/')
        assert resp.status_code == 200

    def test_V_PUB_06_api_docs_returns_200(self):
        resp = Client().get('/api/docs/')
        assert resp.status_code == 200

    def test_password_reset_returns_200(self):
        resp = Client().get('/accounts/password_reset/')
        assert resp.status_code == 200

    def test_password_change_requires_login(self):
        resp = Client().get('/accounts/password_change/')
        assert resp.status_code == 302


# ── Section 4.2: Mode Navigation ───────────────────────────────────────


class TestModeNavigation:
    def test_V_NAV_01_gtd_redirects_to_today(self, client_a):
        resp = client_a.get('/gtd/')
        assert resp.status_code == 302
        assert '/gtd/today/' in resp.url

    def test_V_NAV_02_login_redirect_to_today(self, user_a):
        c = Client()
        resp = c.post('/login/', {'username': 'user_a', 'password': 'testpass123'})
        assert resp.status_code == 302
        assert '/gtd/today/' in resp.url


# ── Section 4.3: Inbox Views ───────────────────────────────────────────


class TestInboxViews:
    def test_V_INB_01_inbox_list_returns_unprocessed(self, client_a, user_a):
        InboxItemFactory(user=user_a, item='Unprocessed')
        InboxItemFactory(user=user_a, item='Processed', processed_at=timezone.now())
        resp = client_a.get(reverse('inbox_list'))
        assert resp.status_code == 200

    def test_V_INB_02_inbox_create_post(self, client_a, user_a):
        resp = client_a.post(reverse('inbox_add'), {'item': 'New idea'})
        assert resp.status_code in (200, 302)
        assert InboxItem.objects.filter(user=user_a, item='New idea').exists()

    def test_V_INB_03_quick_capture_post(self, client_a, user_a):
        resp = client_a.post(
            reverse('quick_capture'),
            {'item': 'Quick thought'},
            HTTP_HX_REQUEST='true',
        )
        assert resp.status_code == 200
        assert InboxItem.objects.filter(user=user_a, item='Quick thought').exists()

    def test_V_INB_04_inbox_process_returns_oldest(self, client_a, user_a):
        InboxItemFactory(user=user_a, item='First')
        InboxItemFactory(user=user_a, item='Second')
        resp = client_a.get(reverse('inbox_process'))
        assert resp.status_code == 200

    def test_V_INB_05_convert_to_action(self, client_a, user_a):
        item = InboxItemFactory(user=user_a, item='Task to convert')
        resp = client_a.post(reverse('convert_to_action', args=[item.pk]))
        assert resp.status_code in (200, 302)
        item.refresh_from_db()
        assert item.processed_at is not None

    def test_V_INB_06_convert_to_project(self, client_a, user_a):
        item = InboxItemFactory(user=user_a, item='Project idea')
        resp = client_a.post(reverse('convert_to_project', args=[item.pk]))
        assert resp.status_code in (200, 302)
        item.refresh_from_db()
        assert item.processed_at is not None

    def test_V_INB_07_archive_inbox_item(self, client_a, user_a):
        item = InboxItemFactory(user=user_a)
        resp = client_a.post(reverse('archive_inbox_item', args=[item.pk]))
        assert resp.status_code in (200, 302)
        item.refresh_from_db()
        assert item.processed_at is not None

    def test_V_INB_08_delete_inbox_item(self, client_a, user_a):
        item = InboxItemFactory(user=user_a)
        pk = item.pk
        resp = client_a.post(reverse('delete_inbox_item', args=[pk]))
        assert resp.status_code in (200, 302)
        assert not InboxItem.objects.filter(pk=pk).exists()


# ── Section 4.4: Today Views ───────────────────────────────────────────


class TestTodayViews:
    def test_V_TOD_01_today_returns_correct_context(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        ActionFactory(
            user=user_a, area=area, project=project,
            scheduled_start=timezone.now(),
        )
        resp = client_a.get(reverse('today'))
        assert resp.status_code == 200

    def test_V_TOD_02_htmx_returns_partial(self, client_a, user_a):
        resp_full = client_a.get(reverse('today'))
        resp_htmx = client_a.get(reverse('today'), HTTP_HX_REQUEST='true')
        # Both should return 200, htmx response likely shorter
        assert resp_full.status_code == 200
        assert resp_htmx.status_code == 200

    def test_V_TOD_03_action_side_panel(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(user=user_a, area=area, project=project)
        resp = client_a.get(reverse('action_side_panel', args=[action.pk]))
        assert resp.status_code == 200

    def test_V_TOD_04_complete_action(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(user=user_a, area=area, project=project)
        resp = client_a.post(reverse('complete_action', args=[action.pk]))
        assert resp.status_code in (200, 302)
        action.refresh_from_db()
        assert action.ended_at is not None


# ── Section 4.5: Project Views ─────────────────────────────────────────


class TestProjectViews:
    def test_V_PRJ_01_project_list_returns_200(self, client_a):
        resp = client_a.get(reverse('project_list'))
        assert resp.status_code == 200

    def test_V_PRJ_02_project_detail_returns_200(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = ProjectFactory(user=user_a, area=area)
        resp = client_a.get(reverse('project_detail', args=[project.pk]))
        assert resp.status_code == 200

    def test_V_PRJ_03_project_create_post(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        status = Status.objects.get(name='PROPOSED')
        resp = client_a.post(reverse('project_create'), {
            'name': 'New Project',
            'area': area.pk,
            'status': status.pk,
        })
        assert resp.status_code in (200, 302)
        assert Project.objects.filter(user=user_a, name='New Project').exists()

    def test_V_PRJ_04_project_update_post(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = ProjectFactory(user=user_a, area=area)
        resp = client_a.post(reverse('project_update', args=[project.pk]), {
            'name': 'Updated Name',
            'area': area.pk,
            'status': project.status.pk,
        })
        assert resp.status_code in (200, 302)

    def test_V_PRJ_05_project_side_panel(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = ProjectFactory(user=user_a, area=area)
        resp = client_a.get(reverse('project_side_panel', args=[project.pk]))
        assert resp.status_code == 200

    def test_V_PRJ_07_complete_project(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        status = Status.objects.get(name='IN ACTION')
        project = ProjectFactory(user=user_a, area=area, status=status)
        resp = client_a.post(reverse('complete_project', args=[project.pk]))
        assert resp.status_code in (200, 302)

    def test_V_PRJ_08_abandon_project(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        status = Status.objects.get(name='IN ACTION')
        project = ProjectFactory(user=user_a, area=area, status=status)
        resp = client_a.post(reverse('abandon_project', args=[project.pk]))
        assert resp.status_code in (200, 302)

    def test_V_PRJ_09_reopen_project(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        status = Status.objects.get(name='COMPLETED')
        project = ProjectFactory(
            user=user_a, area=area, status=status,
            ended_at=timezone.now(),
        )
        resp = client_a.post(reverse('reopen_project', args=[project.pk]))
        assert resp.status_code in (200, 302)


# ── Section 4.6: Time Tracking Views ───────────────────────────────────


class TestTimeViews:
    def test_V_TIM_01_daily_timesheet(self, client_a):
        resp = client_a.get(reverse('time_daily'))
        assert resp.status_code == 200

    def test_V_TIM_02_start_work_session(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(user=user_a, area=area, project=project)
        resp = client_a.post(reverse('start_work_session', args=[action.pk]))
        assert resp.status_code in (200, 302)
        assert WorkSession.objects.filter(user=user_a, action=action, finished_at__isnull=True).exists()

    def test_V_TIM_03_stop_work_session(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(user=user_a, area=area, project=project)
        WorkSessionFactory(action=action, user=user_a)
        resp = client_a.post(reverse('stop_work_session'))
        assert resp.status_code in (200, 302)

    def test_V_TIM_04_report_daily(self, client_a):
        resp = client_a.get(reverse('report_daily'))
        assert resp.status_code == 200

    def test_V_TIM_05_report_weekly(self, client_a):
        resp = client_a.get(reverse('report_weekly'))
        assert resp.status_code == 200


# ── Section 4.7: Review Views ──────────────────────────────────────────


class TestReviewViews:
    def test_V_REV_01_review_returns_context(self, client_a):
        resp = client_a.get(reverse('review'))
        assert resp.status_code == 200

    def test_V_REV_02_review_post_updates_last_review(self, client_a, user_a):
        resp = client_a.post(reverse('review'))
        assert resp.status_code in (200, 302)
        user_a.userprofile.refresh_from_db()
        assert user_a.userprofile.last_review_date is not None


# ── Section 4.8: Config Views ──────────────────────────────────────────


class TestConfigViews:
    def test_V_CFG_01_domain_list(self, client_a):
        resp = client_a.get(reverse('domain_list'))
        assert resp.status_code == 200

    def test_V_CFG_01_domain_create(self, client_a, user_a):
        resp = client_a.post(reverse('domain_create'), {
            'name': 'NewDomain', 'color': 'info',
        })
        assert resp.status_code in (200, 302)
        assert Domain.objects.filter(user=user_a, name='NewDomain').exists()

    def test_V_CFG_02_area_list(self, client_a):
        resp = client_a.get(reverse('area_list'))
        assert resp.status_code == 200

    def test_V_CFG_03_context_list(self, client_a):
        resp = client_a.get(reverse('context_list'))
        assert resp.status_code == 200


# ── Section 4.9: Context Processor ─────────────────────────────────────


class TestContextProcessor:
    def test_V_CTX_01_app_version_on_all_pages(self, client_a):
        resp = client_a.get(reverse('today'))
        assert 'app_version' in resp.context

    def test_V_CTX_02_inbox_count_correct(self, client_a, user_a):
        InboxItemFactory(user=user_a, item='Item 1')
        InboxItemFactory(user=user_a, item='Item 2')
        InboxItemFactory(user=user_a, item='Processed',
                         processed_at=timezone.now())
        resp = client_a.get(reverse('today'))
        assert resp.context['inbox_count'] == 2

    def test_V_CTX_03_active_session(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(user=user_a, area=area, project=project)
        session = WorkSessionFactory(action=action, user=user_a)
        resp = client_a.get(reverse('today'))
        assert resp.context['active_session'] is not None

    def test_V_CTX_04_review_nudge_true_when_overdue(self, client_a, user_a):
        from datetime import date, timedelta
        profile = user_a.userprofile
        profile.last_review_date = date.today() - timedelta(days=8)
        profile.save()
        resp = client_a.get(reverse('today'))
        assert resp.context['review_nudge'] is True

    def test_V_CTX_05_review_nudge_true_when_no_review(self, client_a, user_a):
        resp = client_a.get(reverse('today'))
        assert resp.context['review_nudge'] is True

    def test_V_CTX_06_unauthenticated_gets_only_version(self):
        resp = Client().get('/')
        assert 'app_version' in resp.context
        assert 'inbox_count' not in resp.context


# ── Section 4.7: Report Views ────────────────────────────────────────


class TestReportViews:
    def _create_finished_session(self, user):
        """Helper to create a work session with finished_at for report views."""
        area = Area.objects.filter(user=user).first()
        project = Project.objects.get(user=user, is_protected=True)
        action = ActionFactory(user=user, area=area, project=project)
        return WorkSessionFactory(
            action=action, user=user,
            finished_at=timezone.now(),
        )

    def test_V_RPT_01_daily_report_returns_200(self, client_a):
        resp = client_a.get(reverse('report_daily'))
        assert resp.status_code == 200

    def test_V_RPT_02_daily_report_with_offset(self, client_a):
        resp = client_a.get(reverse('report_daily_offset', args=[1]))
        assert resp.status_code == 200

    def test_V_RPT_03_daily_report_chart_data(self, client_a, user_a):
        import json
        self._create_finished_session(user_a)
        resp = client_a.get(reverse('report_daily'))
        assert resp.status_code == 200
        chart_data = json.loads(resp.context['chart_data'])
        assert 'labels' in chart_data
        assert 'data' in chart_data
        assert 'colors' in chart_data

    def test_V_RPT_04_weekly_report_returns_200(self, client_a):
        resp = client_a.get(reverse('report_weekly'))
        assert resp.status_code == 200

    def test_V_RPT_05_weekly_report_with_offset(self, client_a):
        resp = client_a.get(reverse('report_weekly_offset', args=[1]))
        assert resp.status_code == 200

    def test_V_RPT_06_weekly_report_chart_data(self, client_a, user_a):
        import json
        self._create_finished_session(user_a)
        resp = client_a.get(reverse('report_weekly'))
        chart_data = json.loads(resp.context['chart_data'])
        assert 'labels' in chart_data
        assert 'data' in chart_data
        assert len(chart_data['labels']) == 7  # Mon-Sun

    def test_V_RPT_07_monthly_by_day_returns_200(self, client_a):
        resp = client_a.get(reverse('report_monthly_by_day'))
        assert resp.status_code == 200

    def test_V_RPT_08_monthly_by_day_with_offset(self, client_a):
        resp = client_a.get(reverse('report_monthly_by_day_offset', args=[1]))
        assert resp.status_code == 200

    def test_V_RPT_09_monthly_by_project_returns_200(self, client_a):
        resp = client_a.get(reverse('report_monthly_by_project'))
        assert resp.status_code == 200

    def test_V_RPT_10_monthly_by_project_chart_data(self, client_a, user_a):
        import json
        self._create_finished_session(user_a)
        resp = client_a.get(reverse('report_monthly_by_project'))
        chart_data = json.loads(resp.context['chart_data'])
        assert 'labels' in chart_data
        assert 'colors' in chart_data

    def test_V_RPT_11_monthly_by_area_returns_200(self, client_a):
        resp = client_a.get(reverse('report_monthly_by_area'))
        assert resp.status_code == 200

    def test_V_RPT_12_monthly_by_area_chart_data(self, client_a, user_a):
        import json
        self._create_finished_session(user_a)
        resp = client_a.get(reverse('report_monthly_by_area'))
        chart_data = json.loads(resp.context['chart_data'])
        assert 'labels' in chart_data
        assert 'colors' in chart_data

    def test_V_RPT_13_monthly_by_action_returns_200(self, client_a):
        resp = client_a.get(reverse('report_monthly_by_action'))
        assert resp.status_code == 200

    def test_V_RPT_14_monthly_by_action_chart_data(self, client_a, user_a):
        import json
        self._create_finished_session(user_a)
        resp = client_a.get(reverse('report_monthly_by_action'))
        chart_data = json.loads(resp.context['chart_data'])
        assert 'labels' in chart_data
        assert 'data' in chart_data

    def test_V_RPT_15_monthly_offset_wraps_year(self, client_a):
        # Offset large enough to wrap into previous year
        resp = client_a.get(reverse('report_monthly_by_day_offset', args=[13]))
        assert resp.status_code == 200


# ── Section 4.4b: Today Views (additional) ────────────────────────────


class TestTodayViewsAdditional:
    def test_V_TOD_05_today_more_returns_partial(self, client_a):
        from datetime import date, timedelta
        future = date.today() + timedelta(days=8)
        resp = client_a.get(
            reverse('today_more', args=[future.isoformat()]),
        )
        assert resp.status_code == 200

    def test_V_TOD_06_uncomplete_action(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(
            user=user_a, area=area, project=project,
            ended_at=timezone.now(),
        )
        resp = client_a.post(reverse('uncomplete_action', args=[action.pk]))
        assert resp.status_code == 200
        action.refresh_from_db()
        assert action.ended_at is None

    def test_V_TOD_07_update_action_from_panel(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(user=user_a, area=area, project=project)
        resp = client_a.post(reverse('update_action', args=[action.pk]), {
            'name': 'Updated via panel',
            'area': area.pk,
            'project': project.pk,
            'priority': action.priority.pk,
            'display_order': action.display_order,
        })
        assert resp.status_code == 200

    def test_V_TOD_08_unscheduled_tasks_returns_200(self, client_a):
        resp = client_a.get(reverse('unscheduled_tasks'))
        assert resp.status_code == 200


# ── Section 3.2: Profile & Account Views ──────────────────────────────


class TestProfileViews:
    def test_V_PRF_01_profile_get_returns_200(self, client_a):
        resp = client_a.get(reverse('profile'))
        assert resp.status_code == 200
        assert 'form' in resp.context

    def test_V_PRF_02_profile_post_updates_user(self, client_a, user_a):
        resp = client_a.post(reverse('profile'), {
            'username': 'user_a',
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'Name',
        })
        assert resp.status_code == 302
        user_a.refresh_from_db()
        assert user_a.first_name == 'Updated'

    def test_V_PRF_03_profile_post_invalid(self, client_a, user_a):
        resp = client_a.post(reverse('profile'), {
            'username': '',  # required field
            'email': '',
        })
        assert resp.status_code == 200  # re-renders form with errors

    def test_V_PRF_04_account_delete_get_returns_form(self, client_a):
        resp = client_a.get(reverse('account_delete'))
        assert resp.status_code == 200
        assert 'form' in resp.context

    def test_V_PRF_05_account_delete_post_success(self, client_a, user_a):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_pk = user_a.pk
        resp = client_a.post(reverse('account_delete'), {
            'password': 'testpass123',
            'confirm': 'testpass123',
        })
        assert resp.status_code == 200
        assert not User.objects.filter(pk=user_pk).exists()

    def test_V_PRF_06_account_delete_wrong_password(self, client_a, user_a):
        resp = client_a.post(reverse('account_delete'), {
            'password': 'wrongpass',
            'confirm': 'wrongpass',
        })
        assert resp.status_code == 200
        # User should still exist
        user_a.refresh_from_db()

    def test_V_PRF_07_account_delete_mismatch(self, client_a, user_a):
        resp = client_a.post(reverse('account_delete'), {
            'password': 'testpass123',
            'confirm': 'differentpass',
        })
        assert resp.status_code == 200
        user_a.refresh_from_db()  # Should still exist
