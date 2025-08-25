from django.urls import path
from .views import *

urlpatterns = [
    # Sprint URLs
    path('sprints/', SprintListCreateView.as_view(), name='sprint-list-create'),
    path('sprints/<int:pk>/', SprintDetailUpdateDeleteView.as_view(), name='sprint-detail'),

    # Story URLs
    path('stories/', StoryListCreateView.as_view(), name='story-list-create'),
    path('stories/<int:pk>/', StoryDetailUpdateDeleteView.as_view(), name='story-detail'),

    # Retrospective URLs
    path('retrospectives/', RetrospectiveListCreateView.as_view(), name='retrospective-list-create'),
    path('retrospectives/<int:pk>/', RetrospectiveDetailUpdateDeleteView.as_view(), name='retrospective-detail'),
]
