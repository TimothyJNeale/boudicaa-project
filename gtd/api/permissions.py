# SDS 7.2 — API permissions
from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Object-level permission: user owns the object."""

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.user == request.user
