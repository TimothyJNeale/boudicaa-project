# SDS 2.4, 2.5, 2.6 — Status, Priority, Context
from django.conf import settings
from django.db import models

from .core import COLOR_CHOICES


class Status(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default='secondary')
    activity_level = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gtd_statuses'
        ordering = ['activity_level', 'name']
        verbose_name_plural = 'statuses'

    def __str__(self) -> str:
        return self.name


class Priority(models.Model):
    name = models.CharField(max_length=50, unique=True)
    rank = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gtd_priorities'
        ordering = ['rank', 'name']
        verbose_name_plural = 'priorities'

    def __str__(self) -> str:
        return self.name


class ContextQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(models.Q(user=user) | models.Q(user__isnull=True))

    def system_defaults(self):
        return self.filter(user__isnull=True)


class Context(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ContextQuerySet.as_manager()

    class Meta:
        db_table = 'gtd_contexts'
        unique_together = [['name', 'user']]
        ordering = ['name']

    def __str__(self) -> str:
        return self.name
