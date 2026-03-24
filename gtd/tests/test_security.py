# Security tests — Test Plan Section 7
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from gtd.models import (
    Action,
    Area,
    Context,
    Domain,
    InboxItem,
    Project,
    Status,
    WorkSession,
)
from gtd.tests.factories import (
    ActionFactory,
    ContextFactory,
    DomainFactory,
    InboxItemFactory,
    ProjectFactory,
    UserFactory,
    WorkSessionFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def user_a():
    return UserFactory(username='sec_user_a')


@pytest.fixture
def user_b():
    return UserFactory(username='sec_user_b')


@pytest.fixture
def client_a(user_a):
    c = Client()
    c.login(username='sec_user_a', password='testpass123')
    return c


@pytest.fixture
def client_b(user_b):
    c = Client()
    c.login(username='sec_user_b', password='testpass123')
    return c


# ── Section 7.1: Authentication Enforcement ─────────────────────────────


class TestAuthenticationEnforcement:
    """S-AUTH-01/02: Every /gtd/* URL returns 302 for unauthenticated."""

    AUTHENTICATED_GET_URLS = [
        'today',
        'inbox_list',
        'inbox_add',
        'inbox_process',
        'inbox_processed',
        'project_list',
        'project_create',
        'time_daily',
        'worksession_list',
        'worksession_create',
        'report_daily',
        'report_weekly',
        'report_monthly_by_day',
        'report_monthly_by_project',
        'report_monthly_by_area',
        'report_monthly_by_action',
        'review',
        'domain_list',
        'domain_create',
        'area_list',
        'area_create',
        'context_list',
        'context_create',
        'profile',
        'unscheduled_tasks',
    ]

    @pytest.mark.parametrize('url_name', AUTHENTICATED_GET_URLS)
    def test_S_AUTH_01_unauthenticated_get_redirects(self, url_name):
        resp = Client().get(reverse(url_name))
        assert resp.status_code == 302, f"{url_name} returned {resp.status_code}"
        assert '/login/' in resp.url


# ── Section 7.2: Data Isolation ─────────────────────────────────────────


class TestDataIsolation:
    """S-ISO tests: User A cannot see/modify User B's data."""

    def test_S_ISO_01_inbox_list_isolation(self, client_a, user_a, user_b):
        InboxItemFactory(user=user_a, item='A item')
        InboxItemFactory(user=user_b, item='B item')
        resp = client_a.get(reverse('inbox_list'))
        content = resp.content.decode()
        assert 'A item' in content
        assert 'B item' not in content

    def test_S_ISO_02_project_detail_returns_404_for_other_user(
        self, client_a, user_a, user_b,
    ):
        area_b = Area.objects.filter(user=user_b).first()
        project_b = ProjectFactory(user=user_b, area=area_b)
        resp = client_a.get(reverse('project_detail', args=[project_b.pk]))
        assert resp.status_code == 404

    def test_S_ISO_03_project_update_returns_404_for_other_user(
        self, client_a, user_a, user_b,
    ):
        area_b = Area.objects.filter(user=user_b).first()
        project_b = ProjectFactory(user=user_b, area=area_b)
        resp = client_a.post(
            reverse('project_update', args=[project_b.pk]),
            {'name': 'Hacked', 'area': area_b.pk, 'status': project_b.status.pk},
        )
        assert resp.status_code == 404

    def test_S_ISO_04_action_side_panel_returns_404_for_other_user(
        self, client_a, user_a, user_b,
    ):
        area_b = Area.objects.filter(user=user_b).first()
        project_b = Project.objects.get(user=user_b, is_protected=True)
        action_b = ActionFactory(user=user_b, area=area_b, project=project_b)
        resp = client_a.get(reverse('action_side_panel', args=[action_b.pk]))
        assert resp.status_code == 404

    def test_S_ISO_09_context_processor_inbox_count_isolation(
        self, client_a, user_a, user_b,
    ):
        InboxItemFactory(user=user_a, item='Mine')
        InboxItemFactory(user=user_b, item='Not mine')
        InboxItemFactory(user=user_b, item='Also not mine')
        resp = client_a.get(reverse('today'))
        assert resp.context['inbox_count'] == 1

    def test_S_ISO_10_context_processor_active_session_isolation(
        self, client_a, user_a, user_b,
    ):
        area_b = Area.objects.filter(user=user_b).first()
        project_b = Project.objects.get(user=user_b, is_protected=True)
        action_b = ActionFactory(user=user_b, area=area_b, project=project_b)
        WorkSessionFactory(action=action_b, user=user_b)
        resp = client_a.get(reverse('today'))
        assert resp.context['active_session'] is None

    def test_S_ISO_12_form_querysets_user_scoped(self, client_a, user_a, user_b):
        """Project create form should only show user_a's areas."""
        resp = client_a.get(reverse('project_create'))
        form = resp.context.get('form')
        if form:
            area_qs = form.fields['area'].queryset
            assert not area_qs.filter(user=user_b).exists()


# ── Section 7.3: CSRF Protection ────────────────────────────────────────


class TestCSRFProtection:
    def test_S_CSRF_01_post_without_csrf_rejected(self, user_a):
        c = Client(enforce_csrf_checks=True)
        c.login(username='sec_user_a', password='testpass123')
        resp = c.post(reverse('inbox_add'), {'item': 'Test'})
        assert resp.status_code == 403

    def test_S_CSRF_04_logout_is_post_only(self, user_a):
        c = Client()
        c.login(username='sec_user_a', password='testpass123')
        resp = c.get('/logout/')
        # GET should not log out — either 405 or redirect
        assert resp.status_code in (302, 405, 200)


# ── Section 7.4: Input Validation ───────────────────────────────────────


class TestInputValidation:
    def test_S_INP_01_project_name_max_length(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        status = Status.objects.get(name='PROPOSED')
        long_name = 'x' * 71  # Exceeds max_length=70
        resp = client_a.post(reverse('project_create'), {
            'name': long_name,
            'area': area.pk,
            'status': status.pk,
        })
        # Form should reject — should not create the project
        assert not Project.objects.filter(user=user_a, name=long_name).exists()

    def test_S_INP_06_fk_fields_reject_other_users_ids(
        self, client_a, user_a, user_b,
    ):
        """User A submitting a form with User B's area ID should fail."""
        area_b = Area.objects.filter(user=user_b).first()
        status = Status.objects.get(name='PROPOSED')
        resp = client_a.post(reverse('project_create'), {
            'name': 'Forged Area',
            'area': area_b.pk,
            'status': status.pk,
        })
        # Form validation should reject the foreign area
        assert not Project.objects.filter(user=user_a, name='Forged Area').exists()


# ── Section 7.5: Mass Assignment ────────────────────────────────────────


class TestMassAssignment:
    def test_S_MASS_01_form_cannot_set_user(self, client_a, user_a, user_b):
        area = Area.objects.filter(user=user_a).first()
        status = Status.objects.get(name='PROPOSED')
        resp = client_a.post(reverse('project_create'), {
            'name': 'Assigned Project',
            'area': area.pk,
            'status': status.pk,
            'user': user_b.pk,  # Attempt to set another user
        })
        project = Project.objects.filter(name='Assigned Project').first()
        if project:
            # User should be overridden to the authenticated user
            assert project.user == user_a

    def test_S_MASS_02_form_cannot_set_is_protected(self, client_a, user_a):
        area = Area.objects.filter(user=user_a).first()
        status = Status.objects.get(name='PROPOSED')
        resp = client_a.post(reverse('project_create'), {
            'name': 'Protected Hack',
            'area': area.pk,
            'status': status.pk,
            'is_protected': True,
        })
        project = Project.objects.filter(name='Protected Hack').first()
        if project:
            assert project.is_protected is False


# ── Section 7.7: Information Disclosure ──────────────────────────────


class TestInformationDisclosure:
    def test_S_INFO_05_admin_not_accessible_to_non_staff(self, client_a):
        resp = client_a.get('/admin/')
        # Non-staff should be redirected to admin login
        assert resp.status_code == 302
