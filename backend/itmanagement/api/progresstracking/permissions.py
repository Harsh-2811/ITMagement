from rest_framework import permissions
from api.projects.models import Project

class IsProjectMember(permissions.BasePermission):
    def has_permission(self, request, view):
        project_id = (
            request.query_params.get("project") or request.data.get("project") or ""
        ).strip()

        if not project_id.isdigit():
            return False

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return False

        # return project.team.filter(id=request.user.id).exists()
        return project.members.filter(id=request.user.id).exists()


    def has_object_permission(self, request, view, obj):
        # return obj.project.team.filter(id=request.user.id).exists()
        return obj.project.members.filter(id=request.user.id).exists()



