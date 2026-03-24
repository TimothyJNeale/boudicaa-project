# SDS 2.2, 2.3, 2.11 — Domain, Area, UserProfile
import secrets

from django.conf import settings
from django.db import models

COLOR_CHOICES = [
    ('primary', 'Primary'),
    ('secondary', 'Secondary'),
    ('success', 'Success'),
    ('danger', 'Danger'),
    ('warning', 'Warning'),
    ('info', 'Info'),
    ('dark', 'Dark'),
    ('light', 'Light'),
]


class DomainQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(models.Q(user=user) | models.Q(user__isnull=True))

    def system_defaults(self):
        return self.filter(user__isnull=True)


class Domain(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default='primary')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_protected = models.BooleanField(default=False)

    objects = DomainQuerySet.as_manager()

    class Meta:
        db_table = 'gtd_domains'
        unique_together = [['name', 'user']]
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    @property
    def is_system_default(self) -> bool:
        return self.user is None


class AreaQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(models.Q(user=user) | models.Q(user__isnull=True))

    def system_defaults(self):
        return self.filter(user__isnull=True)


class Area(models.Model):
    name = models.CharField(max_length=100)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_protected = models.BooleanField(default=False)

    objects = AreaQuerySet.as_manager()

    class Meta:
        db_table = 'gtd_areas'
        unique_together = [['name', 'domain', 'user']]
        ordering = ['domain__name', 'name']

    def __str__(self) -> str:
        return f"{self.domain.name} / {self.name}"

    def clean(self) -> None:
        from django.core.exceptions import ValidationError
        super().clean()
        # Area's domain must belong to the same user
        if self.domain_id and self.domain.user != self.user:
            raise ValidationError("Area's domain must belong to the same user.")


class UserProfile(models.Model):
    """SDS 2.11 — One-to-one extension of User."""
    VIEW_CHOICES = [
        ('board', 'Board'),
        ('list', 'List'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    api_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    preferred_project_view = models.CharField(
        max_length=10, choices=VIEW_CHOICES, default='board',
    )
    last_review_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gtd_user_profiles'

    def __str__(self) -> str:
        return f"Profile: {self.user.username}"

    def generate_api_key(self) -> str:
        self.api_key = secrets.token_hex(32)
        self.save(update_fields=['api_key'])
        return self.api_key

    def days_since_review(self) -> int | None:
        if not self.last_review_date:
            return None
        from datetime import date
        return (date.today() - self.last_review_date).days
