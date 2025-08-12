from rest_framework import permissions
from .models import TaskDependency


class IsTaskAssignee(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.assigned_to == request.user


class IsTaskOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, TaskDependency):
            return obj.task.assigned_to == request.user
        return False


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
