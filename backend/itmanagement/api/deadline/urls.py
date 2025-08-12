from django.urls import path
from .views import (
    DeadlineNotificationListCreateView, DeadlineNotificationDetailView,
    run_deadline_processing_now, critical_path_api, deadline_impact_api, adjust_timeline_api
)

urlpatterns = [
    path("notifications/", DeadlineNotificationListCreateView.as_view(), name="deadline-notifications"),
    path("notifications/<int:pk>/", DeadlineNotificationDetailView.as_view(), name="deadline-notification-detail"),
    path("run-now/", run_deadline_processing_now, name="deadline-run-now"),
    path("critical-path/", critical_path_api, name="deadline-critical-path"),
    path("impact/", deadline_impact_api, name="deadline-impact"),
    path("adjust/", adjust_timeline_api, name="deadline-adjust"),
]
