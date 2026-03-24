# Model tests — test IDs trace to SDS and Test Plan
from datetime import date, datetime, time, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
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
    UserProfile,
    WorkSession,
)
from gtd.tests.factories import (
    ActionFactory,
    AreaFactory,
    ContextFactory,
    DomainFactory,
    InboxItemFactory,
    PriorityFactory,
    ProjectFactory,
    StatusFactory,
    UserFactory,
    WorkSessionFactory,
)

pytestmark = pytest.mark.django_db


# ── Section 3.1: Domain (SDS 2.2) ──────────────────────────────────────


class TestDomain:
    def test_M_DOM_01_unique_name_per_user(self):
        """Duplicate domain name for same user rejected."""
        user = UserFactory()
        DomainFactory(name='Work', user=user)
        with pytest.raises(IntegrityError):
            DomainFactory(name='Work', user=user)

    def test_M_DOM_02_color_defaults_to_primary(self):
        domain = DomainFactory()
        assert domain.color == 'primary'

    def test_M_DOM_03_for_user_returns_only_current_users_domains(self):
        user_a = UserFactory()
        user_b = UserFactory()
        domain_a = DomainFactory(user=user_a, name='A Domain')
        DomainFactory(user=user_b, name='B Domain')
        system_domain = DomainFactory(user=None, name='System Domain')

        result = Domain.objects.for_user(user_a)
        assert domain_a in result
        assert system_domain in result
        assert result.filter(user=user_b).count() == 0

    def test_M_DOM_04_cascade_deleting_domain_deletes_areas(self):
        domain = DomainFactory()
        AreaFactory(domain=domain, user=domain.user)
        domain_pk = domain.pk
        domain.delete()
        assert not Area.objects.filter(domain_id=domain_pk).exists()

    def test_domain_str(self):
        domain = DomainFactory(name='Hobbies')
        assert str(domain) == 'Hobbies'

    def test_is_system_default_true_when_no_user(self):
        domain = DomainFactory(user=None)
        assert domain.is_system_default is True

    def test_is_system_default_false_when_user_set(self):
        domain = DomainFactory()
        assert domain.is_system_default is False


# ── Section 3.2: Area (SDS 2.3) ────────────────────────────────────────


class TestArea:
    def test_M_ARE_01_unique_name_per_user(self):
        user = UserFactory()
        domain = DomainFactory(user=user)
        AreaFactory(name='Health', domain=domain, user=user)
        with pytest.raises(IntegrityError):
            AreaFactory(name='Health', domain=domain, user=user)

    def test_M_ARE_02_fk_to_domain_cascade(self):
        domain = DomainFactory()
        area = AreaFactory(domain=domain, user=domain.user)
        area_pk = area.pk
        domain.delete()
        assert not Area.objects.filter(pk=area_pk).exists()

    def test_M_ARE_03_for_user_returns_only_current_users_areas(self):
        user_a = UserFactory()
        user_b = UserFactory()
        domain_a = DomainFactory(user=user_a)
        domain_b = DomainFactory(user=user_b)
        area_a = AreaFactory(domain=domain_a, user=user_a)
        AreaFactory(domain=domain_b, user=user_b)

        result = Area.objects.for_user(user_a)
        assert area_a in result
        assert result.filter(user=user_b).count() == 0

    def test_M_ARE_04_cascade_deleting_area_cascades_to_projects(self):
        area = AreaFactory()
        status = StatusFactory(name='TEST_STATUS')
        ProjectFactory(area=area, user=area.user, status=status)
        area_pk = area.pk
        area.delete()
        assert not Project.objects.filter(area_id=area_pk).exists()

    def test_area_clean_validates_domain_user_match(self):
        user_a = UserFactory()
        user_b = UserFactory()
        domain_b = DomainFactory(user=user_b)
        area = Area(name='Test', domain=domain_b, user=user_a)
        with pytest.raises(ValidationError):
            area.clean()

    def test_area_str(self):
        domain = DomainFactory(name='Work')
        area = AreaFactory(name='Projects', domain=domain, user=domain.user)
        assert str(area) == 'Work / Projects'


# ── Section 3.3: Status (SDS 2.4) ──────────────────────────────────────


class TestStatus:
    def test_M_STA_01_status_is_system_wide(self):
        """Status has no user field — system-wide."""
        status = StatusFactory()
        assert not hasattr(status, 'user')

    def test_M_STA_02_protect_cannot_delete_status_with_projects(self):
        status = StatusFactory(name='IN_USE_STATUS')
        project = ProjectFactory(status=status)
        with pytest.raises(Exception):  # ProtectedError
            status.delete()
        # Project still exists
        assert Project.objects.filter(pk=project.pk).exists()

    def test_M_STA_03_activity_level_field(self):
        status = StatusFactory(name='Active', activity_level=5)
        assert status.activity_level == 5

    def test_status_str(self):
        status = Status.objects.get(name='IN ACTION')
        assert str(status) == 'IN ACTION'


# ── Section 3.4: Priority (SDS 2.5) ────────────────────────────────────


class TestPriority:
    def test_M_PRI_01_priority_is_system_wide(self):
        priority = PriorityFactory()
        assert not hasattr(priority, 'user')

    def test_M_PRI_02_protect_cannot_delete_priority_with_actions(self):
        priority = PriorityFactory(name='TestPriority')
        ActionFactory(priority=priority)
        with pytest.raises(Exception):  # ProtectedError
            priority.delete()

    def test_M_PRI_03_rank_determines_ordering(self):
        p1 = PriorityFactory(name='TestLow', rank=30)
        p2 = PriorityFactory(name='TestHigh', rank=10)
        p3 = PriorityFactory(name='TestMedium', rank=20)
        ordered = list(Priority.objects.filter(pk__in=[p1.pk, p2.pk, p3.pk]).order_by('rank'))
        assert ordered == [p2, p3, p1]


# ── Section 3.5: Context (SDS 2.6) ─────────────────────────────────────


class TestContext:
    def test_M_CTX_01_unique_name_per_user(self):
        user = UserFactory()
        ContextFactory(name='Office', user=user)
        with pytest.raises(IntegrityError):
            ContextFactory(name='Office', user=user)

    def test_M_CTX_02_for_user_returns_only_current_users_contexts(self):
        user_a = UserFactory()
        user_b = UserFactory()
        ctx_a = ContextFactory(name='Home', user=user_a)
        ContextFactory(name='Office', user=user_b)

        result = Context.objects.for_user(user_a)
        assert ctx_a in result
        assert result.filter(user=user_b).count() == 0

    def test_M_CTX_03_set_null_on_action_when_context_deleted(self):
        context = ContextFactory()
        action = ActionFactory(context=context, user=context.user)
        context.delete()
        action.refresh_from_db()
        assert action.context is None


# ── Section 3.6: Project (SDS 2.7) ─────────────────────────────────────


class TestProject:
    @pytest.fixture(autouse=True)
    def _statuses(self):
        """Create statuses needed by project tests."""
        self.proposed = Status.objects.get_or_create(
            name='PROPOSED', defaults={'activity_level': 1, 'color': 'info'}
        )[0]
        self.in_action = Status.objects.get_or_create(
            name='IN ACTION', defaults={'activity_level': 6, 'color': 'success'}
        )[0]
        self.completed = Status.objects.get_or_create(
            name='COMPLETED', defaults={'activity_level': 10, 'color': 'dark'}
        )[0]
        self.abandoned = Status.objects.get_or_create(
            name='ABANDONED', defaults={'activity_level': 11, 'color': 'danger'}
        )[0]
        self.next = Status.objects.get_or_create(
            name='NEXT', defaults={'activity_level': 5, 'color': 'primary'}
        )[0]
        self.someday = Status.objects.get_or_create(
            name='SOMEDAY', defaults={'activity_level': 2, 'color': 'secondary'}
        )[0]

    def test_M_PRJ_01_unique_name_per_user(self):
        user = UserFactory()
        area = AreaFactory(user=user)
        ProjectFactory(name='MyProject', user=user, area=area, status=self.in_action)
        with pytest.raises(IntegrityError):
            ProjectFactory(name='MyProject', user=user, area=area, status=self.in_action)

    def test_M_PRJ_02_unique_slug_per_user(self):
        """Slug auto-generated should also be unique per user."""
        user = UserFactory()
        area = AreaFactory(user=user)
        ProjectFactory(name='Test Project', user=user, area=area, status=self.in_action)
        # Same slug would be generated
        with pytest.raises(IntegrityError):
            ProjectFactory(name='Test Project', user=user, area=area, status=self.in_action)

    def test_M_PRJ_03_slug_auto_generated_from_name(self):
        project = ProjectFactory(name='My Great Project', status=self.in_action)
        assert project.slug == 'my-great-project'

    def test_M_PRJ_04_status_fk_uses_protect(self):
        project = ProjectFactory(status=self.proposed)
        with pytest.raises(Exception):  # ProtectedError
            self.proposed.delete()
        assert Project.objects.filter(pk=project.pk).exists()

    def test_M_PRJ_05_parent_project_fk_uses_set_null(self):
        parent = ProjectFactory(status=self.in_action)
        child = ProjectFactory(
            parent_project=parent, user=parent.user, area=parent.area,
            status=self.in_action,
        )
        parent.delete()
        child.refresh_from_db()
        assert child.parent_project is None

    def test_M_PRJ_06_is_sub_project_true_when_parent_set(self):
        parent = ProjectFactory(status=self.in_action)
        child = ProjectFactory(
            parent_project=parent, user=parent.user, area=parent.area,
            status=self.in_action,
        )
        assert child.is_sub_project is True

    def test_M_PRJ_06_is_sub_project_false_when_no_parent(self):
        project = ProjectFactory(status=self.in_action)
        assert project.is_sub_project is False

    def test_M_PRJ_07_incomplete_action_count(self):
        project = ProjectFactory(status=self.in_action)
        ActionFactory(project=project, user=project.user, area=project.area)
        ActionFactory(project=project, user=project.user, area=project.area)
        ActionFactory(project=project, user=project.user, area=project.area,
                      ended_at=timezone.now())
        assert project.incomplete_action_count == 2

    def test_M_PRJ_08_completed_action_count(self):
        project = ProjectFactory(status=self.in_action)
        ActionFactory(project=project, user=project.user, area=project.area)
        ActionFactory(project=project, user=project.user, area=project.area,
                      ended_at=timezone.now())
        assert project.completed_action_count == 1

    def test_M_PRJ_09_can_complete_safely_false_if_active_sub_projects(self):
        parent = ProjectFactory(status=self.in_action)
        ProjectFactory(
            parent_project=parent, user=parent.user, area=parent.area,
            status=self.in_action,
        )
        assert parent.can_complete_safely is False

    def test_M_PRJ_09_can_complete_safely_true_if_no_active_sub_projects(self):
        parent = ProjectFactory(status=self.in_action)
        ProjectFactory(
            parent_project=parent, user=parent.user, area=parent.area,
            status=self.completed,
        )
        assert parent.can_complete_safely is True

    def test_M_PRJ_10_is_ended_true_for_completed(self):
        project = ProjectFactory(status=self.completed)
        assert project.is_ended is True

    def test_M_PRJ_10_is_ended_true_for_abandoned(self):
        project = ProjectFactory(status=self.abandoned)
        assert project.is_ended is True

    def test_M_PRJ_10_is_ended_false_for_active(self):
        project = ProjectFactory(status=self.in_action)
        assert project.is_ended is False

    def test_M_PRJ_11_is_suitable_parent_false_for_ended(self):
        project = ProjectFactory(status=self.completed)
        assert project.is_suitable_parent is False

    def test_M_PRJ_11_is_suitable_parent_true_for_active(self):
        project = ProjectFactory(status=self.in_action)
        assert project.is_suitable_parent is True

    def test_M_PRJ_13_mark_complete_sets_status_and_ended_at(self):
        project = ProjectFactory(status=self.in_action)
        assert project.ended_at is None
        project.mark_complete('COMPLETED')
        project.refresh_from_db()
        assert project.status.name == 'COMPLETED'
        assert project.ended_at is not None

    def test_M_PRJ_14_valid_transitions_enforced(self):
        """Test that invalid transitions are rejected via clean()."""
        project = ProjectFactory(status=self.proposed)
        project.status = self.completed  # PROPOSED → COMPLETED is invalid
        with pytest.raises(ValidationError, match="Cannot transition"):
            project.clean()

    def test_M_PRJ_14_valid_transition_accepted(self):
        """PROPOSED → IN ACTION is valid."""
        project = ProjectFactory(status=self.proposed)
        project.status = self.in_action
        project.clean()  # Should not raise

    def test_M_PRJ_15_reopen_completed_to_next(self):
        """COMPLETED → NEXT is a special reopen transition."""
        project = ProjectFactory(status=self.completed)
        project.status = self.next
        project.clean()  # Should not raise

    def test_M_PRJ_16_reopen_abandoned_to_in_action(self):
        """ABANDONED → IN ACTION is a special reopen transition."""
        project = ProjectFactory(status=self.abandoned)
        project.status = self.in_action
        project.clean()  # Should not raise

    def test_M_PRJ_17_suitable_parents_excludes_ended(self):
        user = UserFactory()
        area = AreaFactory(user=user)
        active = ProjectFactory(status=self.in_action, user=user, area=area)
        ProjectFactory(status=self.completed, user=user, area=area)
        ProjectFactory(status=self.abandoned, user=user, area=area)

        suitable = Project.objects.filter(user=user).suitable_parents()
        assert active in suitable
        # The provisioned "Open" project is also active, so expect 2
        assert suitable.filter(status__name__in=['COMPLETED', 'ABANDONED']).count() == 0
        assert active in suitable


# ── Section 3.7: Action (SDS 2.8) ──────────────────────────────────────


class TestAction:
    def test_M_ACT_01_display_order_defaults_to_99999(self):
        action = ActionFactory()
        assert action.display_order == 99999

    def test_M_ACT_02_is_overdue_true_when_past_end_and_not_complete(self):
        action = ActionFactory(
            scheduled_end=timezone.now() - timedelta(days=1),
        )
        assert action.is_overdue is True

    def test_M_ACT_02_is_overdue_false_when_complete(self):
        action = ActionFactory(
            scheduled_end=timezone.now() - timedelta(days=1),
            ended_at=timezone.now(),
        )
        assert action.is_overdue is False

    def test_M_ACT_03_is_recurring_true_when_rule_set(self):
        action = ActionFactory(recurrence_rule='RRULE:FREQ=DAILY')
        assert action.is_recurring is True

    def test_M_ACT_03_is_recurring_false_when_no_rule(self):
        action = ActionFactory(recurrence_rule=None)
        assert action.is_recurring is False

    def test_M_ACT_05_overdue_queryset(self):
        overdue = ActionFactory(
            scheduled_end=timezone.now() - timedelta(days=1),
        )
        not_overdue = ActionFactory(
            scheduled_end=timezone.now() + timedelta(days=1),
            user=overdue.user, project=overdue.project, area=overdue.area,
        )
        completed = ActionFactory(
            scheduled_end=timezone.now() - timedelta(days=1),
            ended_at=timezone.now(),
            user=overdue.user, project=overdue.project, area=overdue.area,
        )
        qs = Action.objects.overdue()
        assert overdue in qs
        assert not_overdue not in qs
        assert completed not in qs

    def test_M_ACT_06_incomplete_queryset(self):
        incomplete = ActionFactory()
        complete = ActionFactory(
            ended_at=timezone.now(),
            user=incomplete.user, project=incomplete.project,
            area=incomplete.area,
        )
        qs = Action.objects.incomplete()
        assert incomplete in qs
        assert complete not in qs

    def test_M_ACT_07_unscheduled_standalone_queryset(self):
        user = UserFactory()
        # Use the provisioned "Open" project (is_protected=True)
        open_project = Project.objects.get(user=user, is_protected=True)
        area = open_project.area
        status = Status.objects.get(name='IN ACTION')
        normal_project = ProjectFactory(
            name='Normal', user=user, area=area, status=status,
        )

        standalone = ActionFactory(
            project=open_project, user=user, area=area,
            scheduled_start=None, scheduled_end=None,
        )
        scheduled = ActionFactory(
            project=open_project, user=user, area=area,
            scheduled_start=timezone.now(),
        )
        in_project = ActionFactory(
            project=normal_project, user=user, area=area,
            scheduled_start=None, scheduled_end=None,
        )

        qs = Action.objects.unscheduled_standalone()
        assert standalone in qs
        assert scheduled not in qs
        assert in_project not in qs

    def test_M_ACT_08_area_fk_uses_protect(self):
        action = ActionFactory()
        with pytest.raises(Exception):  # ProtectedError
            action.area.delete()

    def test_M_ACT_09_priority_fk_uses_protect(self):
        priority = PriorityFactory(name='ProtectTest')
        action = ActionFactory(priority=priority)
        with pytest.raises(Exception):
            priority.delete()
        assert Action.objects.filter(pk=action.pk).exists()

    def test_M_ACT_10_project_fk_uses_cascade(self):
        action = ActionFactory()
        action_pk = action.pk
        action.project.delete()
        assert not Action.objects.filter(pk=action_pk).exists()

    def test_M_ACT_12_recurrence_end_is_nullable(self):
        action = ActionFactory(recurrence_end=None)
        assert action.recurrence_end is None

    def test_M_ACT_13_completing_recurring_action_generates_next_instance(self):
        now = timezone.now()
        action = ActionFactory(
            recurrence_rule='RRULE:FREQ=DAILY',
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=1),
        )
        original_count = Action.objects.filter(user=action.user).count()
        action.complete()
        assert Action.objects.filter(user=action.user).count() == original_count + 1
        next_action = Action.objects.filter(
            user=action.user, ended_at__isnull=True, name=action.name,
        ).exclude(pk=action.pk).first()
        assert next_action is not None
        assert next_action.scheduled_start > action.scheduled_start

    def test_action_complete_sets_ended_at(self):
        action = ActionFactory()
        assert action.ended_at is None
        action.complete()
        action.refresh_from_db()
        assert action.ended_at is not None

    def test_action_skip_sets_is_skipped(self):
        action = ActionFactory()
        action.skip()
        action.refresh_from_db()
        assert action.is_skipped is True

    def test_is_complete_property(self):
        action = ActionFactory()
        assert action.is_complete is False
        action.ended_at = timezone.now()
        assert action.is_complete is True

    def test_is_waiting_property(self):
        action = ActionFactory(waiting_on=42)
        assert action.is_waiting is True

    def test_is_actionable_property(self):
        action = ActionFactory()
        assert action.is_actionable is True
        action.is_skipped = True
        assert action.is_actionable is False

    def test_total_time_worked(self):
        action = ActionFactory()
        now = timezone.now()
        WorkSessionFactory(
            action=action, user=action.user,
            started_at=now - timedelta(hours=2),
            finished_at=now - timedelta(hours=1),
        )
        WorkSessionFactory(
            action=action, user=action.user,
            started_at=now - timedelta(minutes=30),
            finished_at=now,
        )
        total = action.total_time_worked
        assert total == timedelta(hours=1, minutes=30)


# ── Section 3.8: InboxItem (SDS 2.9) ───────────────────────────────────


class TestInboxItem:
    def test_M_INB_01_user_field_is_required(self):
        with pytest.raises(IntegrityError):
            InboxItem.objects.create(item='Test', user=None)

    def test_M_INB_02_area_fk_uses_set_null(self):
        area = AreaFactory()
        item = InboxItemFactory(area=area, user=area.user)
        area.delete()
        item.refresh_from_db()
        assert item.area is None

    def test_M_INB_03_processed_at_null_for_unprocessed(self):
        item = InboxItemFactory()
        assert item.processed_at is None
        assert item.is_processed is False

    def test_M_INB_04_mark_processed_records_note(self):
        item = InboxItemFactory()
        item.mark_processed('Converted to action')
        item.refresh_from_db()
        assert item.processed_at is not None
        assert item.processing_note == 'Converted to action'


# ── Section 3.9: WorkSession (SDS 2.10) ────────────────────────────────


class TestWorkSession:
    def test_M_WRK_01_finished_at_null_for_active(self):
        session = WorkSessionFactory()
        assert session.finished_at is None
        assert session.is_active is True

    def test_M_WRK_02_elapsed_time_calculates_correctly(self):
        now = timezone.now()
        session = WorkSessionFactory(
            started_at=now - timedelta(hours=2),
            finished_at=now,
        )
        assert session.elapsed_time == timedelta(hours=2)

    def test_M_WRK_03_action_fk_uses_cascade(self):
        session = WorkSessionFactory()
        session_pk = session.pk
        session.action.delete()
        assert not WorkSession.objects.filter(pk=session_pk).exists()

    def test_elapsed_time_formatted_hours_and_minutes(self):
        now = timezone.now()
        session = WorkSessionFactory(
            started_at=now - timedelta(hours=1, minutes=30),
            finished_at=now,
        )
        assert session.elapsed_time_formatted == '1h 30m'

    def test_elapsed_time_formatted_minutes_only(self):
        now = timezone.now()
        session = WorkSessionFactory(
            started_at=now - timedelta(minutes=45),
            finished_at=now,
        )
        assert session.elapsed_time_formatted == '45m'

    def test_elapsed_minutes(self):
        now = timezone.now()
        session = WorkSessionFactory(
            started_at=now - timedelta(hours=1, minutes=30),
            finished_at=now,
        )
        assert session.elapsed_minutes == 90

    def test_finish_method(self):
        session = WorkSessionFactory()
        assert session.finished_at is None
        session.finish()
        session.refresh_from_db()
        assert session.finished_at is not None


# ── Section 3.10: UserProfile (SDS 2.11) ───────────────────────────────


class TestUserProfile:
    def test_M_USP_01_one_to_one_with_user_cascade(self):
        """Deleting user deletes profile."""
        user = UserFactory()
        profile = UserProfile.objects.get(user=user)
        user_pk = user.pk
        user.delete()
        assert not UserProfile.objects.filter(user_id=user_pk).exists()

    def test_M_USP_02_api_key_auto_generated_via_method(self):
        user = UserFactory()
        profile = UserProfile.objects.get(user=user)
        key = profile.generate_api_key()
        assert key is not None
        assert len(key) == 64  # hex(32) = 64 chars

    def test_M_USP_03_last_review_date_is_nullable(self):
        user = UserFactory()
        profile = UserProfile.objects.get(user=user)
        assert profile.last_review_date is None

    def test_M_USP_04_profile_created_via_signal(self):
        """User provisioning signal creates profile automatically."""
        user = UserFactory()
        assert UserProfile.objects.filter(user=user).exists()

    def test_days_since_review_returns_none_when_no_review(self):
        user = UserFactory()
        profile = UserProfile.objects.get(user=user)
        assert profile.days_since_review() is None

    def test_days_since_review_returns_correct_days(self):
        user = UserFactory()
        profile = UserProfile.objects.get(user=user)
        profile.last_review_date = date.today() - timedelta(days=5)
        profile.save()
        assert profile.days_since_review() == 5


# ── Section 3.11: Deletion Cascade (SDS 2.12) ──────────────────────────


class TestDeletionCascade:
    @pytest.fixture(autouse=True)
    def _statuses(self):
        self.in_action = Status.objects.get_or_create(
            name='IN ACTION', defaults={'activity_level': 6, 'color': 'success'}
        )[0]

    def test_M_CAS_01_deleting_user_deletes_all_data(self):
        user = UserFactory()
        domain = DomainFactory(user=user)
        area = AreaFactory(domain=domain, user=user)
        project = ProjectFactory(area=area, user=user, status=self.in_action)
        action = ActionFactory(project=project, user=user, area=area)
        WorkSessionFactory(action=action, user=user)
        InboxItemFactory(user=user)

        user_pk = user.pk
        # Delete actions first to avoid PROTECT on area FK
        Action.objects.filter(user=user).delete()
        user.delete()

        assert not Domain.objects.filter(user_id=user_pk).exists()
        assert not Area.objects.filter(user_id=user_pk).exists()
        assert not Project.objects.filter(user_id=user_pk).exists()
        assert not Action.objects.filter(user_id=user_pk).exists()
        assert not WorkSession.objects.filter(user_id=user_pk).exists()
        assert not InboxItem.objects.filter(user_id=user_pk).exists()
        assert not UserProfile.objects.filter(user_id=user_pk).exists()

    def test_M_CAS_02_deleting_domain_cascades(self):
        domain = DomainFactory()
        area = AreaFactory(domain=domain, user=domain.user)
        project = ProjectFactory(area=area, user=domain.user, status=self.in_action)
        action = ActionFactory(project=project, user=domain.user, area=area)
        WorkSessionFactory(action=action, user=domain.user)

        # Delete actions first to avoid PROTECT on area/priority FK
        Action.objects.filter(area=area).delete()
        domain.delete()
        assert not Area.objects.filter(pk=area.pk).exists()
        assert not Project.objects.filter(pk=project.pk).exists()

    def test_M_CAS_04_deleting_project_cascades_to_actions_and_sessions(self):
        project = ProjectFactory(status=self.in_action)
        action = ActionFactory(project=project, user=project.user, area=project.area)
        session = WorkSessionFactory(action=action, user=project.user)

        project.delete()
        assert not Action.objects.filter(pk=action.pk).exists()
        assert not WorkSession.objects.filter(pk=session.pk).exists()

    def test_M_CAS_05_deleting_action_cascades_to_sessions(self):
        action = ActionFactory()
        session = WorkSessionFactory(action=action, user=action.user)
        action.delete()
        assert not WorkSession.objects.filter(pk=session.pk).exists()
