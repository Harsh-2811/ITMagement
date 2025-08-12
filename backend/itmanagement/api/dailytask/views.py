from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import DailyTask, TaskDependency, TaskTimeLog, StandupReport
from .serializers import (
    DailyTaskSerializer,
    TaskDependencySerializer,
    TaskTimeLogSerializer,
    StandupReportSerializer
)
from .permissions import IsTaskAssignee, IsTaskOwner, IsOwner  # ← Added IsOwner
from django.db import IntegrityError

# Daily Task Views 

class DailyTaskListCreateView(generics.ListCreateAPIView):
    serializer_class = DailyTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = DailyTask.objects.filter(assigned_to=self.request.user)
        sprint_id = self.request.query_params.get('sprint')
        status = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')

        if sprint_id:
            qs = qs.filter(sprint_id=sprint_id)
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)

        return qs.order_by('-due_date')


    def perform_create(self, serializer):
    # If admin, allow them to assign to others; else default to self
        if self.request.user.is_staff:
            serializer.save()
        else:
            serializer.save(assigned_to=self.request.user)



class DailyTaskDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DailyTaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsTaskAssignee]

    def get_queryset(self):
        return DailyTask.objects.filter(assigned_to=self.request.user)


# Task Dependency Views 

class TaskDependencyListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskDependencySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.request.query_params.get('task')
        qs = TaskDependency.objects.filter(task__assigned_to=self.request.user)
        if task_id:
            try:
                task_id = int(task_id)
                task = DailyTask.objects.get(id=task_id, assigned_to=self.request.user)
                qs = qs.filter(task=task)
            except (ValueError, DailyTask.DoesNotExist):
                raise ValidationError("Task not found or access denied.")
        return qs

    def perform_create(self, serializer):
        task = serializer.validated_data['task']
        if task.assigned_to != self.request.user:
            raise PermissionDenied("You cannot add dependencies to a task you do not own.")
        serializer.save()


class TaskDependencyDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskDependencySerializer
    permission_classes = [permissions.IsAuthenticated, IsTaskOwner]

    def get_queryset(self):
        return TaskDependency.objects.filter(task__assigned_to=self.request.user)


# Task Time Log Views

class TaskTimeLogListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskTimeLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskTimeLog.objects.filter(user=self.request.user).order_by('-date')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TaskTimeLogDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskTimeLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]  # ← Added IsOwner

    def get_queryset(self):
        return TaskTimeLog.objects.filter(user=self.request.user)


# Standup Report Views
class StandupReportListCreateView(generics.ListCreateAPIView):
    serializer_class = StandupReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StandupReport.objects.filter(user=self.request.user).order_by('-date')


    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except IntegrityError:
            raise ValidationError("A standup report for today already exists.")


class StandupReportDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StandupReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]  # ← Added IsOwner

    def get_queryset(self):
        return StandupReport.objects.filter(user=self.request.user)
