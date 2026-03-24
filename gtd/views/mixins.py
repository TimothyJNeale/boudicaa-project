# SDS 4.1 — Base view patterns
from django.contrib.auth.mixins import LoginRequiredMixin


class UserScopedMixin(LoginRequiredMixin):
    """Ensure all querysets are scoped to the current user."""

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
