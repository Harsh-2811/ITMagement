# invoices/permissions.py
from rest_framework.permissions import BasePermission


class IsOwnerOrStaff(BasePermission):
    """Only invoice owner or staff can access object endpoints."""

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or getattr(obj, "owner", None) == request.user
