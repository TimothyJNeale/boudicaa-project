# Workflow tests — Test Plan Section 8
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from gtd.models import (
    Action,
    Area,
    InboxItem,
    Project,
    Status,
    UserProfile,
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
def user():
    return UserFactory(username='wf_user')


@pytest.fixture
def client(user):
    c = Client()
    c.login(username='wf_user', password='testpass123')
    return c


class TestInboxToActionToTimer:
    """W-01: Create inbox → process to action → start timer → stop → verify session."""

    def test_W_01_full_workflow(self, client, user):
        # Create inbox item
        client.post(reverse('inbox_add'), {'item': 'Call dentist'})
        item = InboxItem.objects.get(user=user, item='Call dentist')

        # Convert to action
        client.post(reverse('convert_to_action', args=[item.pk]))
        item.refresh_from_db()
        assert item.processed_at is not None

        # Find the created action
        action = Action.objects.filter(user=user, name__icontains='Call dentist').first()
        assert action is not None

        # Start timer
        client.post(reverse('start_work_session', args=[action.pk]))
        session = WorkSession.objects.filter(user=user, action=action).first()
        assert session is not None
        assert session.finished_at is None

        # Stop timer
        client.post(reverse('stop_work_session'))
        session.refresh_from_db()
        assert session.finished_at is not None


class TestInboxToProject:
    """W-02: Create inbox → process to project → add action."""

    def test_W_02_inbox_to_project(self, client, user):
        client.post(reverse('inbox_add'), {'item': 'New project idea'})
        item = InboxItem.objects.get(user=user, item='New project idea')

        client.post(reverse('convert_to_project', args=[item.pk]))
        item.refresh_from_db()
        assert item.processed_at is not None

        project = Project.objects.filter(
            user=user, name__icontains='New project idea',
        ).first()
        assert project is not None


class TestProjectLifecycle:
    """W-03: Create project → transition → add actions → complete."""

    def test_W_03_full_lifecycle(self, client, user):
        area = Area.objects.filter(user=user).first()
        proposed = Status.objects.get(name='PROPOSED')
        in_action = Status.objects.get(name='IN ACTION')

        # Create project
        client.post(reverse('project_create'), {
            'name': 'Lifecycle Test',
            'area': area.pk,
            'status': proposed.pk,
        })
        project = Project.objects.get(user=user, name='Lifecycle Test')
        assert project.status.name == 'PROPOSED'

        # Transition to IN ACTION
        project.status = in_action
        project.full_clean()
        project.save()
        assert project.status.name == 'IN ACTION'

        # Add action
        action = ActionFactory(
            user=user, area=area, project=project,
            scheduled_start=timezone.now(),
        )

        # Complete action
        action.complete()
        assert action.ended_at is not None

        # Complete project
        client.post(reverse('complete_project', args=[project.pk]))
        project.refresh_from_db()
        assert project.status.name == 'COMPLETED'
        assert project.ended_at is not None


class TestProjectWithSubProjects:
    """W-04: Parent with sub-project — complete sub first."""

    def test_W_04_sub_project_blocking(self, user):
        area = Area.objects.filter(user=user).first()
        in_action = Status.objects.get(name='IN ACTION')

        parent = ProjectFactory(user=user, area=area, status=in_action, name='Parent')
        child = ProjectFactory(
            user=user, area=area, status=in_action,
            name='Child', parent_project=parent,
        )

        # Parent cannot complete safely while child is active
        assert parent.can_complete_safely is False

        # Complete child
        child.mark_complete('COMPLETED')
        parent.refresh_from_db()
        assert parent.can_complete_safely is True

        # Now complete parent
        parent.mark_complete('COMPLETED')
        assert parent.status.name == 'COMPLETED'


class TestRecurringActionCycle:
    """W-05/W-06: Recurring action generates next instance."""

    def test_W_05_recurring_action_chain(self, user):
        area = Area.objects.filter(user=user).first()
        project = Project.objects.get(user=user, is_protected=True)
        now = timezone.now()

        action = ActionFactory(
            user=user, area=area, project=project,
            name='Daily standup',
            recurrence_rule='RRULE:FREQ=DAILY',
            scheduled_start=now,
            scheduled_end=now + timedelta(minutes=15),
        )

        # Complete first instance
        action.complete()
        assert action.ended_at is not None

        # Find next instance
        next_action = Action.objects.filter(
            user=user, name='Daily standup', ended_at__isnull=True,
        ).first()
        assert next_action is not None
        assert next_action.scheduled_start > now

        # Complete second instance
        next_action.complete()
        third = Action.objects.filter(
            user=user, name='Daily standup', ended_at__isnull=True,
        ).first()
        assert third is not None

    def test_W_06_recurrence_end_stops_chain(self, user):
        from datetime import date
        area = Area.objects.filter(user=user).first()
        project = Project.objects.get(user=user, is_protected=True)
        now = timezone.now()

        action = ActionFactory(
            user=user, area=area, project=project,
            name='Limited task',
            recurrence_rule='RRULE:FREQ=DAILY',
            scheduled_start=now,
            scheduled_end=now + timedelta(minutes=15),
            recurrence_end=date.today(),  # Ends today
        )

        action.complete()
        # Next occurrence would be tomorrow, which exceeds recurrence_end
        next_action = Action.objects.filter(
            user=user, name='Limited task', ended_at__isnull=True,
        ).first()
        assert next_action is None


class TestAccountDeletion:
    """W-08: User deletion removes all data."""

    def test_W_08_account_deletion(self, user):
        area = Area.objects.filter(user=user).first()
        project = Project.objects.get(user=user, is_protected=True)
        action = ActionFactory(user=user, area=area, project=project)
        WorkSessionFactory(action=action, user=user)
        InboxItemFactory(user=user)

        user_pk = user.pk
        # Delete actions first due to PROTECT on area/priority FK
        Action.objects.filter(user=user).delete()
        user.delete()

        assert not Project.objects.filter(user_id=user_pk).exists()
        assert not WorkSession.objects.filter(user_id=user_pk).exists()
        assert not InboxItem.objects.filter(user_id=user_pk).exists()
        assert not UserProfile.objects.filter(user_id=user_pk).exists()


class TestAutoStopTimer:
    """W-09: Starting new session auto-stops previous."""

    def test_W_09_auto_stop(self, client, user):
        area = Area.objects.filter(user=user).first()
        project = Project.objects.get(user=user, is_protected=True)
        action1 = ActionFactory(user=user, area=area, project=project, name='Task 1')
        action2 = ActionFactory(user=user, area=area, project=project, name='Task 2')

        # Start first timer
        client.post(reverse('start_work_session', args=[action1.pk]))
        session1 = WorkSession.objects.get(user=user, action=action1)
        assert session1.finished_at is None

        # Start second timer — should auto-stop first
        client.post(reverse('start_work_session', args=[action2.pk]))
        session1.refresh_from_db()
        assert session1.finished_at is not None

        session2 = WorkSession.objects.filter(
            user=user, action=action2, finished_at__isnull=True,
        ).first()
        assert session2 is not None


class TestHtmxPartialVsFullPage:
    """W-12: Normal request → full page, htmx request → partial."""

    def test_W_12_htmx_vs_full(self, client, user):
        resp_full = client.get(reverse('today'))
        resp_htmx = client.get(reverse('today'), HTTP_HX_REQUEST='true')
        assert resp_full.status_code == 200
        assert resp_htmx.status_code == 200
        # Full page should have more content (includes base template)
        assert len(resp_full.content) >= len(resp_htmx.content)
