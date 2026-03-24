# SDS 10.2 — User provisioning signal
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Area, Context, Domain, Project, Status, UserProfile


@receiver(post_save, sender=User)
def provision_new_user(sender, instance: User, created: bool, **kwargs) -> None:
    if not created:
        return

    # Create UserProfile
    UserProfile.objects.create(user=instance)

    # Copy system default domains and their areas
    for default_domain in Domain.objects.system_defaults():
        user_domain = Domain.objects.create(
            name=default_domain.name,
            color=default_domain.color,
            user=instance,
        )
        for default_area in Area.objects.filter(domain=default_domain, user__isnull=True):
            Area.objects.create(
                name=default_area.name,
                domain=user_domain,
                user=instance,
            )

    # Copy system default contexts
    for default_context in Context.objects.system_defaults():
        Context.objects.create(
            name=default_context.name,
            user=instance,
        )

    # Create protected "Open" project
    default_area = Area.objects.filter(user=instance).first()
    if default_area is None:
        raise RuntimeError(
            'Cannot provision user: no system default domain/area found. '
            'Run: python manage.py loaddata gtd/fixtures/seed_data.json'
        )

    try:
        default_status = Status.objects.get(name='IN ACTION')
    except Status.DoesNotExist:
        raise RuntimeError(
            'Cannot provision user: status "IN ACTION" not found. '
            'Run: python manage.py loaddata gtd/fixtures/seed_data.json'
        )

    Project.objects.create(
        name='Open',
        description='Standalone tasks not belonging to any project',
        area=default_area,
        status=default_status,
        user=instance,
        is_protected=True,
    )
