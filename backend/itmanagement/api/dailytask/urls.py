from django.urls import path
from .views import *

urlpatterns = [
    # Daily Tasks
    path('tasks/', DailyTaskListCreateView.as_view(), name='task-list-create'),
    path('tasks/<int:pk>/', DailyTaskDetailUpdateDeleteView.as_view(), name='task-detail'),

    # Task Dependencies
    path('dependencies/', TaskDependencyListCreateView.as_view(), name='dependency-list-create'),
    path('dependencies/<int:pk>/', TaskDependencyDetailUpdateDeleteView.as_view(), name='dependency-detail'),

    # Task Time Logs
    path('timelogs/', TaskTimeLogListCreateView.as_view(), name='timelog-list-create'),
    path('timelogs/<int:pk>/', TaskTimeLogDetailUpdateDeleteView.as_view(), name='timelog-detail'),

    # Standup Reports
    path('standups/', StandupReportListCreateView.as_view(), name='standup-list-create'),
    path('standups/<int:pk>/', StandupReportDetailUpdateDeleteView.as_view(), name='standup-detail'),
]
