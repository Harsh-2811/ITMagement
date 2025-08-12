from django.urls import path
from .views import *

urlpatterns = [
    # Client
    path('clients/', ClientListCreateView.as_view(), name='client-list-create'),

    # Projects
    path('projects/', ProjectListCreateView.as_view(), name='project-list-create'),
    path('projects/<int:pk>/', ProjectDetailUpdateDeleteView.as_view(), name='project-detail'),

    # Project Scope
    path('scopes/', ProjectScopeListCreateView.as_view(), name='project-scope-list-create'),
    path('scopes/<int:pk>/', ProjectScopeDetailView.as_view(), name='project-scope-detail'),

    # Budget
    path('budgets/', BudgetListCreateView.as_view(), name='budget-list-create'),
    path('budgets/<int:pk>/', BudgetDetailView.as_view(), name='budget-detail'),

    # Team Members
    path('team-members/', TeamMemberListCreateView.as_view(), name='team-member-list-create'),

    # Milestones
    path('milestones/', MilestoneListCreateView.as_view(), name='milestone-list-create'),
    path('milestones/<int:pk>/', MilestoneDetailView.as_view(), name='milestone-detail'),
]