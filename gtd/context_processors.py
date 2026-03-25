# SDS 4.2 — Global GTD context
from datetime import date

from django.conf import settings
from django.http import HttpRequest

from gtd.version import __version__ as app_version


def gtd_context(request: HttpRequest) -> dict:
    """Add global GTD context to all templates."""
    context = {
        'app_version': app_version,
        'protected_mode': getattr(settings, 'PROTECTED_MODE', False),
    }

    if not request.user.is_authenticated:
        return context

    from .models import InboxItem, WorkSession

    context.update({
        'inbox_count': InboxItem.objects.filter(
            user=request.user, processed_at__isnull=True,
        ).count(),
        'active_session': WorkSession.objects.filter(
            user=request.user, finished_at__isnull=True,
        ).select_related('action', 'action__project').first(),
        'review_nudge': _should_show_review_nudge(request.user),
    })
    return context


def _should_show_review_nudge(user) -> bool:
    """Return True if it's been 7+ days since last weekly review."""
    profile = getattr(user, 'userprofile', None)
    if not profile or not profile.last_review_date:
        return True
    return (date.today() - profile.last_review_date).days >= 7
