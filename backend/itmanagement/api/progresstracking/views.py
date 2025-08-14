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
from api.projects.models import Project
import os
from django.conf import settings
from .background_tasks import generate_progress_report


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
    # permission_classes = [permissions.IsAuthenticated]

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
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        project_id = request.query_params.get("project")
        if not project_id:
            return Response({"detail": "project query param required"}, status=400)
        get_object_or_404(Project, id=project_id)
        payload = gantt_payload(project_id=int(project_id))
        return Response(payload)

class MetricsAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        project_id = request.query_params.get("project")
        if not project_id:
            return Response({"detail": "project query param required"}, status=400)
        get_object_or_404(Project, id=project_id)
        data = performance_metrics(project_id=int(project_id))
        return Response(data)


class RequestProgressReportView(generics.CreateAPIView):
    """
    API to request generation of a progress report for a specific project.
    """
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Try getting project from multiple possible sources
        project_code = (
            request.data.get("project")
            or request.data.get("project_id")
            or request.query_params.get("project")
            or request.query_params.get("project_id")
        )

        if not project_code:
            return Response(
                {"detail": "Project ID or project_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Normalize to string (avoid UUID JSON serialization issues)
        project_code = str(project_code)

        # Look up project by 'id' or 'project_id' field
        try:
            project = get_object_or_404(Project, pk=project_code)
        except Exception:
            project = get_object_or_404(Project, project_id=project_code)

        # Trigger background task (pass as strings to avoid UUID serialization error)
        generate_progress_report(str(project.id), str(request.user.id), schedule=0)

        return Response(
            {"detail": f"Progress report generation started for project '{project.name}'."},
            status=status.HTTP_202_ACCEPTED
        )


class ProgressReportListView(generics.ListAPIView):
    serializer_class = ProgressReportSerializer
    # permission_classes = [permissions.IsAuthenticated, IsProjectMember]
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        project_id = self.request.query_params.get("project")
        if project_id:
            return ProgressReport.objects.filter(project_id=project_id).order_by("-generated_on")
        return ProgressReport.objects.all().order_by("-generated_on")




class DownloadReportCSVView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = ProgressReport.objects.all()
    lookup_field = "pk"
    serializer_class = ProgressReportSerializer 

    def retrieve(self, request, *args, **kwargs):
        pr = self.get_object()

        if not pr.csv_file:
            return Response({"detail": "No CSV available for this report."}, status=status.HTTP_404_NOT_FOUND)

        abs_path = pr.csv_file.path
        if not os.path.exists(abs_path):
            return Response({"detail": "CSV file not found on server."}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(open(abs_path, "rb"), as_attachment=True, filename=os.path.basename(abs_path))
# class DownloadReportCSVView(generics.RetrieveAPIView):
#     # permission_classes = [permissions.IsAuthenticated, IsProjectMember]
#     permission_classes = [permissions.IsAuthenticated]
#     queryset = ProgressReport.objects.all()
#     lookup_field = "pk"
#     serializer_class = ProgressReportSerializer 

#     def retrieve(self, request, *args, **kwargs):
#         pr = self.get_object()

#         if not pr.csv_file:
#             return Response({"detail": "No CSV available for this report."}, status=status.HTTP_404_NOT_FOUND)

#         media_root = getattr(settings, "MEDIA_ROOT", None)
#         if not media_root:
#             return Response({"detail": "MEDIA_ROOT not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         abs_path = os.path.normpath(os.path.join(media_root, pr.csv_file.lstrip("/\\")))

#         if not os.path.exists(abs_path):
#             return Response({"detail": "CSV file not found on server."}, status=status.HTTP_404_NOT_FOUND)

#         from django.http import FileResponse
#         return FileResponse(open(abs_path, "rb"), as_attachment=True, filename=os.path.basename(abs_path))