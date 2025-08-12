from rest_framework import generics, permissions, status , serializers
from rest_framework.response import Response
from .models import Client, Project, ProjectScope, Budget, TeamMember, Milestone , DeadlineNotification, EscalationLog
from .permissions import IsClientOrReadOnly, IsProjectManager, IsTeamMemberOfProject
from .serializers import (
    ClientSerializer,
    ProjectSerializer,
    ProjectDetailSerializer,
    ProjectScopeSerializer,
    BudgetSerializer,
    TeamMemberCreateSerializer,
    TeamMemberSerializer,
    MilestoneSerializer,
    DeadlineNotificationSerializer,
    EscalationLogSerializer,
    CriticalPathSerializer, 
    DeadlineImpactSerializer
)
from rest_framework import generics, status, serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
import logging
from .utils import compute_critical_path, deadline_impact_assessment, adjust_task_timeline
from .tasks import process_deadline_notifications

class ClientListCreateView(generics.ListCreateAPIView):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
    
        if hasattr(user, "partner_profile") and user.partner_profile.is_active:
            return Client.objects.filter(
                organization=user.partner_profile.organization
            ).order_by('name')
    
        if user.is_staff:
            return Client.objects.all().order_by('name')
    
        return Client.objects.none()



class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectSerializer
        return ProjectDetailSerializer

    def get_queryset(self):
        user = self.request.user
    
        if hasattr(user, "partner_profile") and user.partner_profile.is_active:
            return Project.objects.filter(
            client__organization=user.partner_profile.organization
            ).order_by('-start_date')
    
        if user.is_staff:
            return Project.objects.all().order_by('-start_date')
    
        return Project.objects.none()




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




logger = logging.getLogger(__name__)


#  Deadline Notifications 
class DeadlineNotificationListCreateView(generics.ListCreateAPIView):
    serializer_class = DeadlineNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get("project")
        if project_id and project_id.isdigit():
            return DeadlineNotification.objects.filter(project_id=int(project_id)).order_by("notify_at")
        return DeadlineNotification.objects.none()

    def perform_create(self, serializer):
        serializer.save()


class DeadlineNotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DeadlineNotificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = DeadlineNotification.objects.all()


#  Admin Trigger: Run Deadline Processing 
class RunDeadlineProcessingNowView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        try:
            process_deadline_notifications(schedule=0)
            return Response({"detail": "scheduled"}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"Failed to run deadline processing: {e}")
            return Response({"detail": "error running process"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Critical Path 
class CriticalPathView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        project_id = request.query_params.get("project")
        if not project_id or not project_id.isdigit():
            return Response({"detail": "project param required and must be numeric"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            cp = compute_critical_path(int(project_id))
            serializer = CriticalPathSerializer(cp)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error computing critical path for project {project_id}: {e}")
            return Response({"detail": "error computing critical path"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Deadline Impact
class DeadlineImpactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        task_id = request.query_params.get("task")
        delay_days_str = request.query_params.get("delay_days", "0")

        if not task_id or not task_id.isdigit():
            return Response({"detail": "task param required and must be numeric"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            delay_days = int(delay_days_str)
            if delay_days <= 0:
                return Response({"detail": "delay_days must be positive"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"detail": "delay_days must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            res = deadline_impact_assessment(int(task_id), delay_days)
            serializer = DeadlineImpactSerializer(res)
            if "error" in res:
                return Response(serializer.data, status=status.HTTP_404_NOT_FOUND)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error in deadline impact assessment for task {task_id}: {e}")
            return Response({"detail": "error processing request"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Adjust Timeline 
class AdjustTimelineSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    start_date = serializers.DateField(required=False)
    due_date = serializers.DateField(required=False)


class AdjustTimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = AdjustTimelineSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        task_id = serializer.validated_data.get("task_id")
        new_start = serializer.validated_data.get("start_date")
        new_due = serializer.validated_data.get("due_date")

        try:
            res = adjust_task_timeline(task_id, new_start=new_start, new_due=new_due)
            if "error" in res:
                return Response(res, status=status.HTTP_404_NOT_FOUND)
            return Response(res)
        except Exception as e:
            logger.error(f"Error adjusting timeline for task {task_id}: {e}")
            return Response({"detail": "error processing request"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
