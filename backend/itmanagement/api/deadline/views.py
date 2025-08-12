from rest_framework import generics, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import logging
from .models import DeadlineNotification, EscalationLog
from .serializers import (
    DeadlineNotificationSerializer, EscalationLogSerializer,
    CriticalPathSerializer, DeadlineImpactSerializer
)
from .utils import compute_critical_path, deadline_impact_assessment, adjust_task_timeline
from .tasks import process_deadline_notifications

logger = logging.getLogger(__name__)

class DeadlineNotificationListCreateView(generics.ListCreateAPIView):
    serializer_class = DeadlineNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get("project")
        if project_id and project_id.isdigit():
            return DeadlineNotification.objects.filter(project_id=int(project_id)).order_by("notify_at")
        return DeadlineNotification.objects.none()

    def perform_create(self, serializer):
        serializer.save()

class DeadlineNotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DeadlineNotificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = DeadlineNotification.objects.all()

@api_view(["POST"])
@permission_classes([IsAdminUser])
def run_deadline_processing_now(request):
    """
    Admin-trigger to run the deadline job immediately.
    """
    try:
        process_deadline_notifications(schedule=0)
        return Response({"detail": "scheduled"}, status=202)
    except Exception as e:
        logger.error(f"Failed to run deadline processing: {e}")
        return Response({"detail": "error running process"}, status=500)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def critical_path_api(request):
    project_id = request.query_params.get("project")
    if not project_id or not project_id.isdigit():
        return Response({"detail": "project param required and must be numeric"}, status=400)
    try:
        cp = compute_critical_path(int(project_id))
        serializer = CriticalPathSerializer(cp)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error computing critical path for project {project_id}: {e}")
        return Response({"detail": "error computing critical path"}, status=500)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def deadline_impact_api(request):
    task_id = request.query_params.get("task")
    delay_days_str = request.query_params.get("delay_days", "0")
    if not task_id or not task_id.isdigit():
        return Response({"detail": "task param required and must be numeric"}, status=400)
    try:
        delay_days = int(delay_days_str)
        if delay_days <= 0:
            return Response({"detail": "delay_days must be positive"}, status=400)
    except ValueError:
        return Response({"detail": "delay_days must be an integer"}, status=400)

    try:
        res = deadline_impact_assessment(int(task_id), delay_days)
        serializer = DeadlineImpactSerializer(res)
        if "error" in res:
            return Response(serializer.data, status=404)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error in deadline impact assessment for task {task_id}: {e}")
        return Response({"detail": "error processing request"}, status=500)

class AdjustTimelineSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    start_date = serializers.DateField(required=False)
    due_date = serializers.DateField(required=False)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def adjust_timeline_api(request):
    serializer = AdjustTimelineSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    task_id = serializer.validated_data.get("task_id")
    new_start = serializer.validated_data.get("start_date")
    new_due = serializer.validated_data.get("due_date")

    try:
        res = adjust_task_timeline(task_id, new_start=new_start, new_due=new_due)
        if "error" in res:
            return Response(res, status=404)
        return Response(res)
    except Exception as e:
        logger.error(f"Error adjusting timeline for task {task_id}: {e}")
        return Response({"detail": "error processing request"}, status=500)
