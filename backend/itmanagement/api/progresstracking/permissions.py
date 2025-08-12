from rest_framework import permissions
from projects.models import Project

class IsProjectMember(permissions.BasePermission):
    """
    Custom permission to check if user is a member of the project.
    """

    def has_permission(self, request, view):
        project_id = request.query_params.get("project") or request.data.get("project")
        if not project_id:
            return False  # project param is mandatory for access

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return False
        
        # Here implement your own project membership logic
        return project.members.filter(id=request.user.id).exists()

    def has_object_permission(self, request, view, obj):
        # For object-level permissions, check if user belongs to obj.project
        return obj.project.members.filter(id=request.user.id).exists()
