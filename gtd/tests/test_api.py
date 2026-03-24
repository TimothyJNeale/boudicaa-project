# API tests — SDS Section 7, Test Plan Section 6
import pytest
from django.test import Client
from rest_framework.test import APIClient

from gtd.models import (
    Action,
    Area,
    InboxItem,
    Priority,
    Project,
    Status,
    UserProfile,
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
    return UserFactory(username='api_user_a')


@pytest.fixture
def user_b():
    return UserFactory(username='api_user_b')


@pytest.fixture
def api_client_a(user_a):
    c = APIClient()
    c.force_authenticate(user=user_a)
    return c


@pytest.fixture
def api_client_b(user_b):
    c = APIClient()
    c.force_authenticate(user=user_b)
    return c


# ── Section 6.1: Authentication ─────────────────────────────────────────


class TestAPIAuthentication:
    def test_A_AUTH_01_valid_api_key_authenticates(self, user_a):
        profile = UserProfile.objects.get(user=user_a)
        key = profile.generate_api_key()
        c = APIClient()
        resp = c.get('/api/v1/inbox/', HTTP_AUTHORIZATION=f'Bearer {key}')
        assert resp.status_code == 200

    def test_A_AUTH_02_invalid_api_key_returns_401(self):
        c = APIClient()
        resp = c.get('/api/v1/inbox/', HTTP_AUTHORIZATION='Bearer invalid-key')
        assert resp.status_code in (401, 403)

    def test_A_AUTH_03_missing_header_falls_through(self):
        """Without API key or session, should get 401/403."""
        c = APIClient()
        resp = c.get('/api/v1/inbox/')
        assert resp.status_code in (401, 403)

    def test_A_AUTH_04_session_authentication_works(self, user_a):
        c = APIClient()
        c.login(username='api_user_a', password='testpass123')
        resp = c.get('/api/v1/inbox/')
        assert resp.status_code == 200

    def test_A_AUTH_05_unauthenticated_returns_401(self):
        c = APIClient()
        resp = c.get('/api/v1/inbox/')
        assert resp.status_code in (401, 403)


# ── Section 6.2: Permissions ────────────────────────────────────────────


class TestAPIPermissions:
    def test_A_PERM_01_user_a_cannot_access_user_b_objects(
        self, api_client_a, user_a, user_b,
    ):
        area_b = Area.objects.filter(user=user_b).first()
        project_b = ProjectFactory(user=user_b, area=area_b)
        resp = api_client_a.get(f'/api/v1/projects/{project_b.pk}/')
        assert resp.status_code == 404

    def test_A_PERM_02_user_can_access_own_objects(
        self, api_client_a, user_a,
    ):
        area = Area.objects.filter(user=user_a).first()
        project = ProjectFactory(user=user_a, area=area)
        resp = api_client_a.get(f'/api/v1/projects/{project.pk}/')
        assert resp.status_code == 200


# ── Section 6.3: ViewSets ──────────────────────────────────────────────


class TestAPIViewSets:
    def test_A_VS_01_queryset_filters_by_user(self, api_client_a, user_a, user_b):
        InboxItemFactory(user=user_a, item='A item')
        InboxItemFactory(user=user_b, item='B item')
        resp = api_client_a.get('/api/v1/inbox/')
        data = resp.json()
        items = [r['item'] for r in data['results']]
        assert 'A item' in items
        assert 'B item' not in items

    def test_A_VS_02_perform_create_sets_user(self, api_client_a, user_a):
        resp = api_client_a.post('/api/v1/inbox/', {'item': 'API created'})
        assert resp.status_code == 201
        item = InboxItem.objects.get(item='API created')
        assert item.user == user_a

    def test_A_VS_03_priority_read_only(self, api_client_a):
        resp = api_client_a.post('/api/v1/priorities/', {'name': 'New', 'rank': 99})
        assert resp.status_code == 405  # Method Not Allowed

    def test_A_VS_03_status_read_only(self, api_client_a):
        resp = api_client_a.post(
            '/api/v1/statuses/',
            {'name': 'New', 'activity_level': 99},
        )
        assert resp.status_code == 405

    def test_A_VS_05_pagination_works(self, api_client_a, user_a):
        for i in range(3):
            InboxItemFactory(user=user_a, item=f'Item {i}')
        resp = api_client_a.get('/api/v1/inbox/')
        data = resp.json()
        assert 'count' in data
        assert 'results' in data

    def test_priorities_list(self, api_client_a):
        resp = api_client_a.get('/api/v1/priorities/')
        assert resp.status_code == 200
        assert resp.json()['count'] >= 5  # Seed priorities

    def test_statuses_list(self, api_client_a):
        resp = api_client_a.get('/api/v1/statuses/')
        assert resp.status_code == 200
        assert resp.json()['count'] >= 11  # Seed statuses


# ── API Key Regeneration ────────────────────────────────────────────────


class TestAPIKeyRegeneration:
    def test_A_API_08_regenerate_creates_new_key(self, api_client_a, user_a):
        profile = UserProfile.objects.get(user=user_a)
        old_key = profile.generate_api_key()

        resp = api_client_a.post('/api/v1/user/api-key/regenerate/')
        assert resp.status_code == 200
        data = resp.json()
        assert 'api_key' in data
        assert data['api_key'] != old_key

        profile.refresh_from_db()
        assert profile.api_key == data['api_key']


# ── Cross-User API Isolation ────────────────────────────────────────────


class TestAPICrossUserIsolation:
    def test_S_ISO_05_api_list_isolation(self, api_client_a, user_a, user_b):
        area_a = Area.objects.filter(user=user_a).first()
        area_b = Area.objects.filter(user=user_b).first()
        ProjectFactory(user=user_a, area=area_a, name='A Project')
        ProjectFactory(user=user_b, area=area_b, name='B Project')

        resp = api_client_a.get('/api/v1/projects/')
        names = [p['name'] for p in resp.json()['results']]
        assert 'A Project' in names
        assert 'B Project' not in names

    def test_S_ISO_06_api_detail_isolation(self, api_client_a, user_b):
        area_b = Area.objects.filter(user=user_b).first()
        project_b = ProjectFactory(user=user_b, area=area_b)
        resp = api_client_a.get(f'/api/v1/projects/{project_b.pk}/')
        assert resp.status_code == 404

    def test_S_ISO_07_api_update_isolation(self, api_client_a, user_b):
        area_b = Area.objects.filter(user=user_b).first()
        project_b = ProjectFactory(user=user_b, area=area_b)
        resp = api_client_a.patch(
            f'/api/v1/projects/{project_b.pk}/',
            {'name': 'Hacked'},
        )
        assert resp.status_code == 404

    def test_S_ISO_08_api_delete_isolation(self, api_client_a, user_b):
        item_b = InboxItemFactory(user=user_b)
        resp = api_client_a.delete(f'/api/v1/inbox/{item_b.pk}/')
        assert resp.status_code == 404

    def test_S_MASS_04_api_create_cannot_set_user(
        self, api_client_a, user_a, user_b,
    ):
        resp = api_client_a.post('/api/v1/inbox/', {
            'item': 'Test item',
            'user': user_b.pk,
        })
        if resp.status_code == 201:
            item = InboxItem.objects.get(item='Test item')
            assert item.user == user_a  # Should be overridden


# ── Section 7.4: ViewSet Custom Actions ───────────────────────────────


class TestInboxViewSetActions:
    def test_A_INB_01_convert_to_action(self, api_client_a, user_a):
        item = InboxItemFactory(user=user_a, item='Task to convert via API')
        resp = api_client_a.post(f'/api/v1/inbox/{item.pk}/convert_to_action/')
        assert resp.status_code == 201
        item.refresh_from_db()
        assert item.processed_at is not None
        assert Action.objects.filter(user=user_a, name='Task to convert via API').exists()

    def test_A_INB_02_convert_to_project(self, api_client_a, user_a):
        item = InboxItemFactory(user=user_a, item='Project idea via API')
        resp = api_client_a.post(f'/api/v1/inbox/{item.pk}/convert_to_project/')
        assert resp.status_code == 201
        item.refresh_from_db()
        assert item.processed_at is not None
        assert Project.objects.filter(user=user_a, name='Project idea via API').exists()

    def test_A_INB_03_archive(self, api_client_a, user_a):
        item = InboxItemFactory(user=user_a)
        resp = api_client_a.post(f'/api/v1/inbox/{item.pk}/archive/')
        assert resp.status_code == 200
        item.refresh_from_db()
        assert item.processed_at is not None

    def test_A_INB_04_queryset_excludes_processed(self, api_client_a, user_a):
        from django.utils import timezone
        InboxItemFactory(user=user_a, item='Active')
        InboxItemFactory(user=user_a, item='Done', processed_at=timezone.now())
        resp = api_client_a.get('/api/v1/inbox/')
        items = [r['item'] for r in resp.json()['results']]
        assert 'Active' in items
        assert 'Done' not in items


class TestActionViewSetActions:
    def test_A_ACT_01_today_actions(self, api_client_a, user_a):
        from datetime import date
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        ActionFactory(user=user_a, area=area, project=project, scheduled_start=date.today())
        resp = api_client_a.get('/api/v1/actions/today/')
        assert resp.status_code == 200

    def test_A_ACT_02_overdue_actions(self, api_client_a, user_a):
        resp = api_client_a.get('/api/v1/actions/overdue/')
        assert resp.status_code == 200

    def test_A_ACT_03_complete_action(self, api_client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(user=user_a, area=area, project=project)
        resp = api_client_a.post(f'/api/v1/actions/{action.pk}/complete/')
        assert resp.status_code == 200
        action.refresh_from_db()
        assert action.ended_at is not None

    def test_A_ACT_04_filter_by_project(self, api_client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        ActionFactory(user=user_a, area=area, project=project)
        resp = api_client_a.get(f'/api/v1/actions/?project={project.pk}')
        assert resp.status_code == 200

    def test_A_ACT_05_filter_complete(self, api_client_a, user_a):
        resp = api_client_a.get('/api/v1/actions/?complete=false')
        assert resp.status_code == 200


class TestProjectViewSetActions:
    def test_A_PRJ_01_project_actions_list(self, api_client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = ProjectFactory(user=user_a, area=area)
        ActionFactory(user=user_a, area=area, project=project)
        resp = api_client_a.get(f'/api/v1/projects/{project.pk}/actions/')
        assert resp.status_code == 200

    def test_A_PRJ_02_complete_project(self, api_client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        status_obj = Status.objects.get(name='IN ACTION')
        project = ProjectFactory(user=user_a, area=area, status=status_obj)
        resp = api_client_a.post(f'/api/v1/projects/{project.pk}/complete/')
        assert resp.status_code == 200
        project.refresh_from_db()
        assert project.status.name == 'COMPLETED'

    def test_A_PRJ_03_complete_project_with_actions_move_to_open(self, api_client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        status_obj = Status.objects.get(name='IN ACTION')
        project = ProjectFactory(user=user_a, area=area, status=status_obj)
        action = ActionFactory(user=user_a, area=area, project=project)
        open_project = Project.objects.get(user=user_a, is_protected=True)
        resp = api_client_a.post(
            f'/api/v1/projects/{project.pk}/complete/',
            {'action_handling': 'move_to_open'},
        )
        assert resp.status_code == 200
        action.refresh_from_db()
        assert action.project == open_project

    def test_A_PRJ_04_complete_blocked_by_sub_projects(self, api_client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        status_obj = Status.objects.get(name='IN ACTION')
        parent = ProjectFactory(user=user_a, area=area, status=status_obj)
        ProjectFactory(user=user_a, area=area, status=status_obj, parent_project=parent)
        resp = api_client_a.post(f'/api/v1/projects/{parent.pk}/complete/')
        assert resp.status_code == 409

    def test_A_PRJ_05_abandon_project(self, api_client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        status_obj = Status.objects.get(name='IN ACTION')
        project = ProjectFactory(user=user_a, area=area, status=status_obj)
        resp = api_client_a.post(
            f'/api/v1/projects/{project.pk}/abandon/',
            {'reason': 'No longer relevant'},
        )
        assert resp.status_code == 200
        project.refresh_from_db()
        assert project.status.name == 'ABANDONED'
        assert 'No longer relevant' in project.notes

    def test_A_PRJ_06_reopen_project(self, api_client_a, user_a):
        from django.utils import timezone
        area = Area.objects.filter(user=user_a).first()
        status_obj = Status.objects.get(name='COMPLETED')
        project = ProjectFactory(
            user=user_a, area=area, status=status_obj,
            ended_at=timezone.now(),
        )
        resp = api_client_a.post(
            f'/api/v1/projects/{project.pk}/reopen/',
            {'status': 'IN ACTION'},
        )
        assert resp.status_code == 200
        project.refresh_from_db()
        assert project.status.name == 'IN ACTION'
        assert project.ended_at is None

    def test_A_PRJ_07_reopen_invalid_status(self, api_client_a, user_a):
        from django.utils import timezone
        area = Area.objects.filter(user=user_a).first()
        status_obj = Status.objects.get(name='COMPLETED')
        project = ProjectFactory(
            user=user_a, area=area, status=status_obj,
            ended_at=timezone.now(),
        )
        resp = api_client_a.post(
            f'/api/v1/projects/{project.pk}/reopen/',
            {'status': 'PROPOSED'},
        )
        assert resp.status_code == 400

    def test_A_PRJ_08_excludes_protected(self, api_client_a, user_a):
        """Protected 'Open' project should not appear in project list."""
        resp = api_client_a.get('/api/v1/projects/')
        names = [p['name'] for p in resp.json()['results']]
        assert 'Open' not in names

    def test_A_PRJ_09_filter_by_status(self, api_client_a, user_a):
        resp = api_client_a.get('/api/v1/projects/?status=IN ACTION')
        assert resp.status_code == 200


class TestWorkSessionViewSetActions:
    def test_A_WS_01_active_session(self, api_client_a, user_a):
        resp = api_client_a.get('/api/v1/sessions/active/')
        assert resp.status_code == 200

    def test_A_WS_02_start_session(self, api_client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(user=user_a, area=area, project=project)
        resp = api_client_a.post(f'/api/v1/sessions/start/{action.pk}/')
        assert resp.status_code == 201
        from gtd.models import WorkSession
        assert WorkSession.objects.filter(user=user_a, finished_at__isnull=True).exists()

    def test_A_WS_03_stop_session(self, api_client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(user=user_a, area=area, project=project)
        WorkSessionFactory(action=action, user=user_a)
        resp = api_client_a.post('/api/v1/sessions/stop/')
        assert resp.status_code == 200

    def test_A_WS_04_stop_no_active(self, api_client_a):
        resp = api_client_a.post('/api/v1/sessions/stop/')
        assert resp.status_code == 400

    def test_A_WS_05_start_stops_existing(self, api_client_a, user_a):
        """Starting a new session auto-stops any active one."""
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action1 = ActionFactory(user=user_a, area=area, project=project)
        action2 = ActionFactory(user=user_a, area=area, project=project)
        WorkSessionFactory(action=action1, user=user_a)
        resp = api_client_a.post(f'/api/v1/sessions/start/{action2.pk}/')
        assert resp.status_code == 201
        from gtd.models import WorkSession
        active = WorkSession.objects.filter(user=user_a, finished_at__isnull=True)
        assert active.count() == 1
        assert active.first().action == action2


# ── Review Report Generator ───────────────────────────────────────────


class TestReviewReportGenerator:
    def test_A_REV_01_generate_report(self, api_client_a, user_a):
        resp = api_client_a.post('/api/v1/review/generate/')
        assert resp.status_code == 200
        data = resp.json()
        assert 'generated_at' in data
        assert 'inbox' in data
        assert 'overdue' in data
        assert 'stalled_projects' in data
        assert 'time_summary' in data
        assert 'highlights' in data

    def test_A_REV_02_report_inbox_summary(self, api_client_a, user_a):
        InboxItemFactory(user=user_a, item='Pending 1')
        InboxItemFactory(user=user_a, item='Pending 2')
        resp = api_client_a.post('/api/v1/review/generate/')
        data = resp.json()
        assert data['inbox']['count'] == 2

    def test_A_REV_03_report_highlights(self, api_client_a, user_a):
        from django.utils import timezone
        area = Area.objects.filter(user=user_a).first()
        project = Project.objects.get(user=user_a, is_protected=True)
        action = ActionFactory(user=user_a, area=area, project=project)
        action.complete()
        resp = api_client_a.post('/api/v1/review/generate/')
        data = resp.json()
        assert len(data['highlights']) >= 1

    def test_A_REV_04_report_unauthenticated(self):
        from rest_framework.test import APIClient
        resp = APIClient().post('/api/v1/review/generate/')
        assert resp.status_code in (401, 403)


# ── UserProfile API ──────────────────────────────────────────────────


class TestUserProfileAPI:
    def test_A_PROF_01_get_profile(self, api_client_a, user_a):
        resp = api_client_a.get('/api/v1/user/profile/')
        assert resp.status_code == 200
        data = resp.json()
        assert 'preferred_project_view' in data
        assert 'days_since_review' in data
        assert 'api_key' not in data

    def test_A_PROF_02_update_profile(self, api_client_a, user_a):
        resp = api_client_a.patch(
            '/api/v1/user/profile/',
            {'preferred_project_view': 'list'},
            format='json',
        )
        assert resp.status_code == 200
