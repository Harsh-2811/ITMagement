from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from .models import Sprint, Story, Retrospective
from .serializers import SprintSerializer, StorySerializer, RetrospectiveSerializer
from .permissions import IsProjectMemberOrReadOnly

# Sprint Views 
class SprintListCreateView(generics.ListCreateAPIView):
    serializer_class = SprintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get('project')
        if project_id:
            return Sprint.objects.filter(project_id=project_id).order_by('-start_date')
        return Sprint.objects.all()


class SprintDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SprintSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMemberOrReadOnly]
    queryset = Sprint.objects.all()

# Story Views 
class StoryListCreateView(generics.ListCreateAPIView):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        sprint_id = self.request.query_params.get('sprint')
        project_id = self.request.query_params.get('project')
        filters = {}
        if sprint_id:
            filters['sprint_id'] = sprint_id
        if project_id:
            filters['project_id'] = project_id
        return Story.objects.filter(**filters)


class StoryDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Story.objects.all()

# Retrospective Views 
class RetrospectiveListCreateView(generics.ListCreateAPIView):
    serializer_class = RetrospectiveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Retrospective.objects.all()

    def perform_create(self, serializer):
        sprint = serializer.validated_data['sprint']
        if Retrospective.objects.filter(sprint=sprint).exists():
            raise ValidationError("Retrospective already exists for this sprint.")
        serializer.save()


class RetrospectiveDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RetrospectiveSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Retrospective.objects.all()
