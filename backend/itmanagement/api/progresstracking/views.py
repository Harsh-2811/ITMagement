from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.core.paginator import Paginator
from .models import ProgressUpdate, ProgressReport
from .serializers import ProgressUpdateSerializer, ProgressReportSerializer
from .permissions import IsProjectMember
from .services import burndown_series, gantt_payload, performance_metrics
from projects.models import Project
import os
from django.conf import settings

class ProgressUpdateListCreateView(generics.ListCreateAPIView):
    serializer_class = ProgressUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_queryset(self):
        project_id = self.request.query_params.get("project")
        last_check = self.request.query_params.get("since")  # ISO datetime string
        queryset = ProgressUpdate.objects.select_related('updated_by', 'task', 'milestone').all()

        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if last_check:
            dt = parse_datetime(last_check)
            if dt:
                queryset = queryset.filter(timestamp__gt=dt)
        return queryset.order_by("-timestamp")

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)

class ProgressUpdateDetailView(generics.RetrieveUpdateAPIView):
    queryset = ProgressUpdate.objects.all()
    serializer_class = ProgressUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

class BurndownAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, *args, **kwargs):
        project_id = request.query_params.get("project")
        days = int(request.query_params.get("days", 30))
        if not project_id:
            return Response({"detail": "project query param required"}, status=400)
        get_object_or_404(Project, id=project_id)
        series = burndown_series(project_id=int(project_id), days=days)
        return Response({"project": project_id, "series": series})

class GanttAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, *args, **kwargs):
        project_id = request.query_params.get("project")
        if not project_id:
            return Response({"detail": "project query param required"}, status=400)
        get_object_or_404(Project, id=project_id)
        payload = gantt_payload(project_id=int(project_id))
        return Response(payload)

class MetricsAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, *args, **kwargs):
        project_id = request.query_params.get("project")
        if not project_id:
            return Response({"detail": "project query param required"}, status=400)
        get_object_or_404(Project, id=project_id)
        data = performance_metrics(project_id=int(project_id))
        return Response(data)

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, IsProjectMember])
def request_progress_report(request):
    """
    Enqueue background job to generate a progress report.
    POST JSON: {"project": <id>}
    Response: report queued (report_id if available)
    """
    project_id = request.data.get("project") or request.query_params.get("project")
    if not project_id:
        return Response({"detail": "project param required"}, status=400)
    get_object_or_404(Project, id=project_id)
    user_id = request.user.id
    from .background_tasks import generate_progress_report  # Import here to avoid circular imports
    job = generate_progress_report(project_id, user_id, schedule=0)
    return Response({"detail": "Report generation scheduled."}, status=202)

class ProgressReportListView(generics.ListAPIView):
    serializer_class = ProgressReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_queryset(self):
        project_id = self.request.query_params.get("project")
        if not project_id:
            return ProgressReport.objects.none()
        return ProgressReport.objects.filter(project_id=project_id).order_by("-generated_on")

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsProjectMember])
def download_report_csv(request, pk):
    """
    Download CSV file for a ProgressReport (if csv_file exists).
    PK is ProgressReport id.
    """
    pr = get_object_or_404(ProgressReport, id=pk)
    if not pr.csv_file:
        return Response({"detail": "No CSV available for this report."}, status=404)
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if not media_root:
        return Response({"detail": "MEDIA_ROOT not configured"}, status=500)
    abs_path = os.path.normpath(os.path.join(media_root, pr.csv_file.lstrip("/\\")))
    if not os.path.exists(abs_path):
        return Response({"detail": "CSV file not found on server."}, status=404)
    from django.http import FileResponse
    return FileResponse(open(abs_path, "rb"), as_attachment=True, filename=os.path.basename(abs_path))
