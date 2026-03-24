# Shared test fixtures — seed data required for user provisioning signal
import pytest

from gtd.models import Area, Context, Domain, Priority, Status


@pytest.fixture(autouse=True)
def seed_reference_data(db):
    """Create seed data needed by the user provisioning signal.

    The signal (signals.py) requires:
    - Status 'IN ACTION' to exist (for the Open project)
    - System default domains/areas (user=None) to copy to new users
    - System default contexts (user=None) to copy to new users

    We create the full seed data set to match production (seed_data.json)
    plus system defaults that the provisioning signal copies.
    """
    # Statuses
    statuses = [
        ('PROPOSED', 'info', 1),
        ('SOMEDAY', 'secondary', 2),
        ('LONG', 'secondary', 3),
        ('WAITING', 'warning', 4),
        ('NEXT', 'primary', 5),
        ('IN ACTION', 'success', 6),
        ('BACK BURNER', 'info', 7),
        ('PAUSED', 'warning', 8),
        ('SUSPENDED', 'danger', 9),
        ('COMPLETED', 'dark', 10),
        ('ABANDONED', 'danger', 11),
    ]
    for name, color, level in statuses:
        Status.objects.get_or_create(
            name=name, defaults={'color': color, 'activity_level': level},
        )

    # Priorities
    priorities = [
        ('Critical', 1),
        ('High', 2),
        ('Medium', 3),
        ('Low', 4),
        ('Someday', 5),
    ]
    for name, rank in priorities:
        Priority.objects.get_or_create(
            name=name, defaults={'rank': rank},
        )

    # System default domain and area (user=None) — copied by provisioning signal
    default_domain, _ = Domain.objects.get_or_create(
        name='Personal', user=None, defaults={'color': 'primary'},
    )
    Area.objects.get_or_create(
        name='General', domain=default_domain, user=None,
    )

    # System default context
    Context.objects.get_or_create(name='Anywhere', user=None)
