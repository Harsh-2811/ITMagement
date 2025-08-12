from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Client, Project, ProjectScope, Budget, TeamMember, Milestone
from .permissions import IsClientOrReadOnly, IsProjectManager, IsTeamMemberOfProject
from .serializers import (
    ClientSerializer,
    ProjectSerializer,
    ProjectDetailSerializer,
    ProjectScopeSerializer,
    BudgetSerializer,
    TeamMemberCreateSerializer,
    TeamMemberSerializer,
    MilestoneSerializer
)

#  Client View 
class ClientListCreateView(generics.ListCreateAPIView):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Client.objects.all().order_by('name')

# Project View 
class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectSerializer
        return ProjectDetailSerializer

    def get_queryset(self):
        user = self.request.user
        return Project.objects.filter(client__email=user.email).order_by('-start_date')


class ProjectDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]
    queryset = Project.objects.all()

#  Project Scope 
class ProjectScopeListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectScopeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProjectScope.objects.all()


class ProjectScopeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectScopeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ProjectScope.objects.all()

#  Budget 
class BudgetListCreateView(generics.ListCreateAPIView):
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.all()


class BudgetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Budget.objects.all()

# Team Member 
class TeamMemberListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TeamMemberCreateSerializer
        return TeamMemberSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get('project')
        if project_id:
            return TeamMember.objects.filter(project_id=project_id)
        return TeamMember.objects.all()

# Milestone 
class MilestoneListCreateView(generics.ListCreateAPIView):
    serializer_class = MilestoneSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        project_id = self.request.query_params.get('project')
        if project_id and TeamMember.objects.filter(user=user, project_id=project_id).exists():
            return Milestone.objects.filter(project_id=project_id).order_by('start_date')
        return Milestone.objects.none()

class MilestoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeamMemberOfProject]
