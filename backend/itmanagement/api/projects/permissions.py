# permissions.py

from rest_framework import permissions
from .models import Project, TeamMember


class IsClientOrReadOnly(permissions.BasePermission):
    """
    Allow only the client related to the project to read it.
    """

    def has_object_permission(self, request, view, obj):
        # Safe methods like GET are allowed for matching clients
        if request.method in permissions.SAFE_METHODS:
            return obj.client.email == request.user.email
        return False


class IsProjectManager(permissions.BasePermission):
    """
    Allow only project managers to update or manage the project.
    """

    def has_object_permission(self, request, view, obj):
        return TeamMember.objects.filter(
            user=request.user,
            project=obj,
            role="Project Manager"
        ).exists()


class IsTeamMemberOfProject(permissions.BasePermission):
    """
    Allow access only to team members of the project.
    """

    def has_object_permission(self, request, view, obj):
        return TeamMember.objects.filter(
            user=request.user,
            project=obj.project
        ).exists()
