from rest_framework import permissions

class IsProjectMemberOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in permissions.SAFE_METHODS:
            return True
        return user in obj.project.members.all() or user == obj.project.owner
