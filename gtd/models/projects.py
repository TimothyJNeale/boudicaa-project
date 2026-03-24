# SDS 2.7 — Project model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class ProjectQuerySet(models.QuerySet):
    def suitable_parents(self):
        return self.exclude(status__name__in=['COMPLETED', 'ABANDONED'])


class Project(models.Model):
    VALID_TRANSITIONS = {
        'PROPOSED': ['SOMEDAY', 'LONG', 'WAITING', 'NEXT', 'IN ACTION', 'ABANDONED'],
        'SOMEDAY': ['PROPOSED', 'LONG', 'WAITING', 'NEXT', 'IN ACTION', 'ABANDONED'],
        'LONG': ['SOMEDAY', 'WAITING', 'NEXT', 'IN ACTION', 'ABANDONED'],
        'WAITING': ['SOMEDAY', 'LONG', 'NEXT', 'IN ACTION', 'SUSPENDED', 'ABANDONED'],
        'NEXT': ['SOMEDAY', 'LONG', 'WAITING', 'IN ACTION', 'ABANDONED'],
        'IN ACTION': ['WAITING', 'NEXT', 'BACK BURNER', 'PAUSED', 'SUSPENDED', 'COMPLETED', 'ABANDONED'],
        'BACK BURNER': ['LONG', 'NEXT', 'IN ACTION', 'PAUSED', 'SUSPENDED', 'COMPLETED', 'ABANDONED'],
        'PAUSED': ['NEXT', 'IN ACTION', 'BACK BURNER', 'SUSPENDED', 'COMPLETED', 'ABANDONED'],
        'SUSPENDED': ['WAITING', 'NEXT', 'IN ACTION', 'ABANDONED'],
        'COMPLETED': [],
        'ABANDONED': [],
    }

    name = models.CharField(max_length=70)
    slug = models.SlugField(max_length=50, null=True, blank=True, db_index=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    area = models.ForeignKey('gtd.Area', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.ForeignKey('gtd.Status', on_delete=models.PROTECT)
    parent_project = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_protected = models.BooleanField(default=False, db_index=True)

    objects = ProjectQuerySet.as_manager()

    class Meta:
        db_table = 'gtd_projects'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'user'],
                name='unique_project_name_per_user',
            ),
            models.UniqueConstraint(
                fields=['slug', 'user'],
                name='unique_project_slug_per_user',
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=False)
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        # Validate status transition
        if self.pk:
            try:
                old = Project.objects.get(pk=self.pk)
            except Project.DoesNotExist:
                pass
            else:
                old_status = old.status.name
                new_status = self.status.name
                if old_status != new_status:
                    # Allow reopen transitions as special cases
                    if old_status in ('COMPLETED', 'ABANDONED') and new_status in ('NEXT', 'IN ACTION'):
                        pass
                    elif new_status not in self.VALID_TRANSITIONS.get(old_status, []):
                        raise ValidationError(
                            f"Cannot transition from {old_status} to {new_status}."
                        )

    @property
    def is_sub_project(self) -> bool:
        return self.parent_project is not None

    @property
    def incomplete_action_count(self) -> int:
        return self.action_set.filter(ended_at__isnull=True).count()

    @property
    def completed_action_count(self) -> int:
        return self.action_set.filter(ended_at__isnull=False).count()

    @property
    def total_action_count(self) -> int:
        return self.action_set.count()

    @property
    def can_complete_safely(self) -> bool:
        return not Project.objects.filter(
            parent_project=self,
        ).exclude(status__name__in=['COMPLETED', 'ABANDONED']).exists()

    @property
    def is_ended(self) -> bool:
        return self.status.name in ('COMPLETED', 'ABANDONED')

    @property
    def is_suitable_parent(self) -> bool:
        return not self.is_ended

    def next_scheduled_start(self):
        action = self.action_set.filter(
            ended_at__isnull=True,
            scheduled_start__isnull=False,
        ).order_by('scheduled_start').first()
        return action.scheduled_start if action else None

    def mark_complete(self, status_name: str) -> None:
        from .workflow import Status
        self.status = Status.objects.get(name=status_name)
        self.ended_at = timezone.now()
        self.save(update_fields=['status', 'ended_at', 'updated_at'])
