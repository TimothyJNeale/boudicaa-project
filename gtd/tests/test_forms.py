# Form tests — SDS Section 11, Test Plan Section 5
from datetime import timedelta

import pytest
from django.utils import timezone

from gtd.forms import (
    AccountDeletionForm,
    ActionForm,
    ActionQuickAddForm,
    AreaForm,
    ContextForm,
    DomainForm,
    InboxForm,
    ProjectForm,
    WorkSessionForm,
)
from gtd.models import Area, Context, Domain, Priority, Project, Status
from gtd.tests.factories import (
    ActionFactory,
    AreaFactory,
    DomainFactory,
    ProjectFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


class TestProjectForm:
    def test_FM_01_accepts_user_kwarg_and_sets_on_save(self):
        user = UserFactory()
        area = Area.objects.filter(user=user).first()
        status = Status.objects.get(name='PROPOSED')
        form = ProjectForm(
            data={'name': 'Test Project', 'area': area.pk, 'status': status.pk},
            user=user,
        )
        assert form.is_valid(), form.errors
        project = form.save()
        assert project.user == user

    def test_FM_02_area_grouped_by_domain_for_current_user(self):
        user = UserFactory()
        other_user = UserFactory()
        other_domain = DomainFactory(user=other_user, name='OtherDomain')
        AreaFactory(domain=other_domain, user=other_user, name='OtherArea')

        form = ProjectForm(user=user)
        area_qs = form.fields['area'].queryset
        assert area_qs.filter(user=user).exists()
        assert not area_qs.filter(user=other_user).exists()

    def test_FM_03_project_queryset_filtered_to_current_user(self):
        user = UserFactory()
        other_user = UserFactory()
        ProjectFactory(user=other_user, area=Area.objects.filter(user=other_user).first())

        form = ProjectForm(user=user)
        parent_qs = form.fields['parent_project'].queryset
        assert not parent_qs.filter(user=other_user).exists()


class TestActionForm:
    def test_FM_04_includes_recurrence_fields(self):
        user = UserFactory()
        form = ActionForm(user=user)
        assert 'recurrence_rule' in form.fields
        assert 'recurrence_end' in form.fields

    def test_FM_05_querysets_filtered_to_current_user(self):
        user = UserFactory()
        other_user = UserFactory()

        form = ActionForm(user=user)
        assert not form.fields['project'].queryset.filter(user=other_user).exists()
        assert not form.fields['context'].queryset.filter(user=other_user).exists()

    def test_action_form_saves_with_user(self):
        user = UserFactory()
        area = Area.objects.filter(user=user).first()
        project = Project.objects.get(user=user, is_protected=True)
        priority = Priority.objects.get(name='Medium')

        form = ActionForm(
            data={
                'name': 'Test Action',
                'project': project.pk,
                'area': area.pk,
                'priority': priority.pk,
                'display_order': 99999,
            },
            user=user,
        )
        assert form.is_valid(), form.errors
        action = form.save()
        assert action.user == user


class TestInboxForm:
    def test_FM_06_item_field_present(self):
        """InboxForm has an item field. The model allows blank, so test valid submission."""
        user = UserFactory()
        form = InboxForm(data={'item': 'Remember to call dentist'}, user=user)
        assert form.is_valid(), form.errors

    def test_inbox_form_saves_with_user(self):
        user = UserFactory()
        form = InboxForm(data={'item': 'Buy milk'}, user=user)
        assert form.is_valid(), form.errors
        item = form.save()
        assert item.user == user


class TestWorkSessionForm:
    def test_FM_07_valid_session_times(self):
        user = UserFactory()
        action = ActionFactory(user=user, area=Area.objects.filter(user=user).first(),
                               project=Project.objects.get(user=user, is_protected=True))
        now = timezone.now()
        form = WorkSessionForm(
            data={
                'action': action.pk,
                'started_at': now - timedelta(hours=1),
                'finished_at': now,
            },
            user=user,
        )
        assert form.is_valid(), form.errors

    def test_work_session_action_queryset_filtered(self):
        user = UserFactory()
        other_user = UserFactory()
        ActionFactory(user=other_user,
                      area=Area.objects.filter(user=other_user).first(),
                      project=Project.objects.get(user=other_user, is_protected=True))

        form = WorkSessionForm(user=user)
        assert not form.fields['action'].queryset.filter(user=other_user).exists()


class TestAccountDeletionForm:
    def test_FM_08_requires_password_and_confirmation(self):
        user = UserFactory()
        form = AccountDeletionForm(data={}, user=user)
        assert not form.is_valid()
        assert 'password' in form.errors
        assert 'confirm' in form.errors

    def test_FM_08_rejects_incorrect_password(self):
        user = UserFactory()
        form = AccountDeletionForm(
            data={'password': 'wrongpass', 'confirm': 'wrongpass'},
            user=user,
        )
        assert not form.is_valid()

    def test_FM_08_accepts_correct_password(self):
        user = UserFactory()
        form = AccountDeletionForm(
            data={'password': 'testpass123', 'confirm': 'testpass123'},
            user=user,
        )
        assert form.is_valid(), form.errors

    def test_FM_08_rejects_mismatched_passwords(self):
        user = UserFactory()
        form = AccountDeletionForm(
            data={'password': 'testpass123', 'confirm': 'different'},
            user=user,
        )
        assert not form.is_valid()


class TestActionQuickAddForm:
    def test_FM_09_accepts_minimal_fields(self):
        user = UserFactory()
        project = Project.objects.get(user=user, is_protected=True)
        priority = Priority.objects.get(name='Medium')
        form = ActionQuickAddForm(
            data={'name': 'Quick task', 'priority': priority.pk},
            user=user, project=project,
        )
        assert form.is_valid(), form.errors
        action = form.save()
        assert action.project == project
        assert action.area == project.area
        assert action.user == user


class TestDomainForm:
    def test_domain_form_saves_with_user(self):
        user = UserFactory()
        form = DomainForm(data={'name': 'New Domain', 'color': 'success'}, user=user)
        assert form.is_valid(), form.errors
        domain = form.save()
        assert domain.user == user


class TestAreaForm:
    def test_area_form_domain_queryset_filtered(self):
        user = UserFactory()
        other_user = UserFactory()

        form = AreaForm(user=user)
        assert not form.fields['domain'].queryset.filter(user=other_user).exists()

    def test_area_form_saves_with_user(self):
        user = UserFactory()
        # Use a domain that belongs to this user (not system default)
        domain = Domain.objects.filter(user=user).exclude(user__isnull=True).first()
        form = AreaForm(data={'name': 'New Area', 'domain': domain.pk}, user=user)
        assert form.is_valid(), form.errors
        area = form.save()
        assert area.user == user


class TestContextForm:
    def test_context_form_saves_with_user(self):
        user = UserFactory()
        form = ContextForm(data={'name': 'New Context'}, user=user)
        assert form.is_valid(), form.errors
        context = form.save()
        assert context.user == user


class TestFM10AllFormsRejectMissingRequired:
    def test_project_form_rejects_missing_name(self):
        user = UserFactory()
        form = ProjectForm(data={}, user=user)
        assert not form.is_valid()
        assert 'name' in form.errors

    def test_action_form_rejects_missing_name(self):
        user = UserFactory()
        form = ActionForm(data={}, user=user)
        assert not form.is_valid()
        assert 'name' in form.errors

    def test_domain_form_rejects_missing_name(self):
        user = UserFactory()
        form = DomainForm(data={}, user=user)
        assert not form.is_valid()
        assert 'name' in form.errors

    def test_context_form_rejects_missing_name(self):
        user = UserFactory()
        form = ContextForm(data={}, user=user)
        assert not form.is_valid()
        assert 'name' in form.errors
