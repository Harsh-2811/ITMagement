from django.urls import path
from .views import *

urlpatterns = [
    path("burndown/", BurndownAPIView.as_view(), name="progress-burndown"),
    path("gantt/", GanttAPIView.as_view(), name="progress-gantt"),
    path("metrics/", MetricsAPIView.as_view(), name="progress-metrics"),
    path("reports/request/", request_progress_report, name="progress-request-report"),
    path("reports/", ProgressReportListView.as_view(), name="progress-report-list"),
    path("reports/<int:pk>/download/", download_report_csv, name="progress-report-download"),
    path("progress/", ProgressUpdateListCreateView.as_view(), name="progress-list-create"),
    path("progress/<int:pk>/", ProgressUpdateDetailView.as_view(), name="progress-detail"),
]
