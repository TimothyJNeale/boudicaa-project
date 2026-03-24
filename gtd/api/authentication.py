# SDS 7.1 — API key authentication
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from gtd.models import UserProfile


class APIKeyAuthentication(BaseAuthentication):
    """Authenticate via Authorization: Bearer <api_key> header."""

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None

        key = auth_header[7:]
        try:
            profile = UserProfile.objects.select_related('user').get(api_key=key)
        except UserProfile.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')

        return (profile.user, None)
