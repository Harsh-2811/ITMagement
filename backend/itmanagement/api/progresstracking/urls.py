from django.urls import path
from .views import *

urlpatterns = [
    path("burndown/", BurndownAPIView.as_view(), name="progress-burndown"),
    path("gantt/", GanttAPIView.as_view(), name="progress-gantt"),
    path("metrics/", MetricsAPIView.as_view(), name="progress-metrics"),
    path("reports/", ProgressReportListView.as_view(), name="progress-report-list"),
    path("progress/", ProgressUpdateListCreateView.as_view(), name="progress-list-create"),
    path("progress/<int:pk>/", ProgressUpdateDetailView.as_view(), name="progress-detail"),
    path('progress-report/request/', RequestProgressReportView.as_view(), name='request-progress-report'),
    path('progress-report/list/', ProgressReportListView.as_view(), name='progress-report-list'),
    path('progress-report/download/<int:pk>/', DownloadReportCSVView.as_view(), name='download-progress-report-csv'),
]
