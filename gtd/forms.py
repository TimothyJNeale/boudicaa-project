# SDS 11 — Form definitions
from django import forms
from django.contrib.auth.models import User

from .models import (
    Action,
    Area,
    Context,
    Domain,
    InboxItem,
    Project,
    WorkSession,
)


class GroupedAreaChoiceField(forms.ModelChoiceField):
    """Area choice field grouped by domain."""

    def label_from_instance(self, obj: Area) -> str:
        return obj.name

    def _get_choices(self):
        if not hasattr(self, '_choices_cache'):
            self._choices_cache = self._build_grouped_choices()
        return self._choices_cache

    def _set_choices(self, value):
        pass

    choices = property(_get_choices, _set_choices)

    def _build_grouped_choices(self):
        choices = [('', '---------')]
        if self.queryset is None:
            return choices
        domains = {}
        for area in self.queryset.select_related('domain').order_by('domain__name', 'name'):
            domain_name = area.domain.name
            if domain_name not in domains:
                domains[domain_name] = []
            domains[domain_name].append((area.pk, area.name))
        for domain_name, area_choices in domains.items():
            choices.append((domain_name, area_choices))
        return choices


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'notes', 'area', 'status', 'parent_project']

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['area'] = GroupedAreaChoiceField(
            queryset=Area.objects.for_user(self.user),
        )
        self.fields['parent_project'].queryset = Project.objects.filter(
            user=self.user,
        ).suitable_parents()
        self.fields['parent_project'].required = False

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.user = self.user
        if commit:
            instance.save()
        return instance


class ActionForm(forms.ModelForm):
    # SDS 11.2
    class Meta:
        model = Action
        fields = [
            'name', 'notes', 'project', 'area', 'priority', 'context',
            'scheduled_start', 'scheduled_end', 'time_budgeted',
            'display_order', 'is_skipped', 'waiting_on',
            'recurrence_rule', 'recurrence_end',
        ]

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['area'] = GroupedAreaChoiceField(
            queryset=Area.objects.for_user(self.user),
        )
        self.fields['project'].queryset = Project.objects.filter(user=self.user)
        self.fields['context'].queryset = Context.objects.for_user(self.user)
        self.fields['context'].required = False
        self.fields['scheduled_start'].required = False
        self.fields['scheduled_end'].required = False
        self.fields['time_budgeted'].required = False
        self.fields['waiting_on'].required = False
        self.fields['recurrence_rule'].required = False
        self.fields['recurrence_end'].required = False

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.user = self.user
        if commit:
            instance.save()
        return instance


class ActionQuickAddForm(forms.ModelForm):
    """SDS 11.1 — Minimal form for adding actions from project page."""
    class Meta:
        model = Action
        fields = ['name', 'priority', 'scheduled_start', 'scheduled_end']

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop('user')
        self.project = kwargs.pop('project')
        super().__init__(*args, **kwargs)
        self.fields['scheduled_start'].required = False
        self.fields['scheduled_end'].required = False

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.user = self.user
        instance.project = self.project
        instance.area = self.project.area
        if commit:
            instance.save()
        return instance


class InboxForm(forms.ModelForm):
    class Meta:
        model = InboxItem
        fields = ['item', 'area']

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['area'] = GroupedAreaChoiceField(
            queryset=Area.objects.for_user(self.user),
            required=False,
        )

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.user = self.user
        if commit:
            instance.save()
        return instance


class DomainForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ['name', 'color']

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.user = self.user
        if commit:
            instance.save()
        return instance


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ['name', 'domain']

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['domain'].queryset = Domain.objects.filter(user=self.user)
        # Set user on instance so Area.clean() can validate domain-user match
        if self.instance:
            self.instance.user = self.user

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.user = self.user
        if commit:
            instance.save()
        return instance


class ContextForm(forms.ModelForm):
    class Meta:
        model = Context
        fields = ['name']

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.user = self.user
        if commit:
            instance.save()
        return instance


class WorkSessionForm(forms.ModelForm):
    class Meta:
        model = WorkSession
        fields = ['action', 'started_at', 'finished_at', 'notes']

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['action'].queryset = Action.objects.filter(user=self.user)
        self.fields['finished_at'].required = False
        self.fields['notes'].required = False

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.user = self.user
        if commit:
            instance.save()
        return instance


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']


class AccountDeletionForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm')
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")
        if password and not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password.")
        return cleaned_data
