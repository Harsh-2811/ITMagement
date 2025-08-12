from django.urls import path
from . import views

app_name = "projects"

urlpatterns = [
    # Client
    path("clients/", views.ClientListCreateView.as_view(), name="client-list-create"),

    # Projects
    path("projects/", views.ProjectListCreateView.as_view(), name="project-list-create"),
    path("projects/<int:pk>/", views.ProjectDetailUpdateDeleteView.as_view(), name="project-detail"),

    # Project Scope
    path("scopes/", views.ProjectScopeListCreateView.as_view(), name="project-scope-list-create"),
    path("scopes/<int:pk>/", views.ProjectScopeDetailView.as_view(), name="project-scope-detail"),

    # Budget
    path("budgets/", views.BudgetListCreateView.as_view(), name="budget-list-create"),
    path("budgets/<int:pk>/", views.BudgetDetailView.as_view(), name="budget-detail"),

    # Team Members
    path("team-members/", views.TeamMemberListCreateView.as_view(), name="team-member-list-create"),

    # Milestones
    path("milestones/", views.MilestoneListCreateView.as_view(), name="milestone-list-create"),
    path("milestones/<int:pk>/", views.MilestoneDetailView.as_view(), name="milestone-detail"),

    # Deadline Notifications
    path("notifications/", views.DeadlineNotificationListCreateView.as_view(), name="deadline-notifications"),
    path("notifications/<int:pk>/", views.DeadlineNotificationDetailView.as_view(), name="deadline-notification-detail"),

    # Deadline Admin Actions
    path("run-now/", views.RunDeadlineProcessingNowView.as_view(), name="deadline-run-now"),

    # Critical Path & Impact
    path("critical-path/", views.CriticalPathView.as_view(), name="deadline-critical-path"),
    path("impact/", views.DeadlineImpactView.as_view(), name="deadline-impact"),

    # Adjust Timeline
    path("adjust/", views.AdjustTimelineView.as_view(), name="deadline-adjust"),
]