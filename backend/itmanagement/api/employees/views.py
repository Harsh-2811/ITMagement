from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from api.users.models import User
from api.organizations.models import Organization
from api.partners.models import Partner
from datetime import datetime , date , timedelta
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .models import *
from .serializers import *
from .utils import approve_leave, reject_leave, accrue_monthly_leave, generate_payroll_run , compute_utilization, utilization_band, recommend_employees, project_time_split, forecast_gaps

from rest_framework.views import APIView
class IsMainPartnerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return Partner.objects.filter(user=request.user, role='main_partner').exists()

class EmployeeInviteView(generics.CreateAPIView):
    serializer_class = EmployeeInviteSerializer
    permission_classes = [permissions.IsAuthenticated, IsMainPartnerOrAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Get the organization
            partner = Partner.objects.filter(user=request.user, role='main_partner').first()
            if not partner:
                return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
            organization = partner.organization
            temp_password = get_random_string(length=12)

            user = User.objects.create(
                username=serializer.validated_data['email'],
                email=serializer.validated_data['email'],
                first_name=serializer.validated_data['first_name'],
                last_name=serializer.validated_data['last_name'],
                phone=serializer.validated_data.get('phone', ''),
                user_type='employee',
                password=make_password(temp_password),
                is_verified=False
            )

            employee = Employee.objects.create(
                user=user,
                organization=organization,
                role=serializer.validated_data['role'],
                permissions=serializer.validated_data['permissions'],
                invited_by=request.user
            )

            try:
                send_mail(
                    subject=f'You are invited to join {organization.name}',
                    message=f"""
Hi {user.first_name},

You have been invited to join {organization.name} as a {employee.role}.

Login credentials:
Username: {user.username}
Temporary Password: {temp_password}

Please login and change your password after first login.

Thanks,
{request.user.first_name}
                    """,
                    from_email='admin@example.com',
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send email: {e}")

            return Response({
                'message': 'Employee invited successfully',
                'employee_id': employee.id,
                'email': user.email,
                'temp_password': temp_password  # You can remove this in production
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class DepartmentListCreateView(generics.ListCreateAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

class JobRoleListCreateView(generics.ListCreateAPIView):
    queryset = JobRole.objects.all()
    serializer_class = JobRoleSerializer
    permission_classes = [permissions.IsAuthenticated]

class JobRoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = JobRole.objects.all()
    serializer_class = JobRoleSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmployeeListCreateView(generics.ListCreateAPIView):
    queryset = Employee.objects.select_related("user", "department", "job_role")
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]

class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Employee.objects.select_related("user", "department", "job_role")
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmployeeContractListCreateView(generics.ListCreateAPIView):
    queryset = EmployeeContract.objects.select_related("employee")
    serializer_class = EmployeeContractSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

class EmployeeContractDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EmployeeContract.objects.select_related("employee")
    serializer_class = EmployeeContractSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


class EmployeeDocumentListCreateView(generics.ListCreateAPIView):
    queryset = EmployeeDocument.objects.select_related("employee")
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

class EmployeeDocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EmployeeDocument.objects.select_related("employee")
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]



class SkillListCreateView(generics.ListCreateAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated]

class SkillDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmployeeSkillListCreateView(generics.ListCreateAPIView):
    queryset = EmployeeSkill.objects.select_related("employee", "skill")
    serializer_class = EmployeeSkillSerializer
    permission_classes = [permissions.IsAuthenticated]

class EmployeeSkillDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EmployeeSkill.objects.select_related("employee", "skill")
    serializer_class = EmployeeSkillSerializer
    permission_classes = [permissions.IsAuthenticated]


class CertificationListCreateView(generics.ListCreateAPIView):
    queryset = Certification.objects.select_related("employee")
    serializer_class = CertificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

class CertificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Certification.objects.select_related("employee")
    serializer_class = CertificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]



class PerformanceCycleListCreateView(generics.ListCreateAPIView):
    queryset = PerformanceCycle.objects.all()
    serializer_class = PerformanceCycleSerializer
    permission_classes = [permissions.IsAuthenticated]

class PerformanceCycleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PerformanceCycle.objects.all()
    serializer_class = PerformanceCycleSerializer
    permission_classes = [permissions.IsAuthenticated]


class PerformanceGoalListCreateView(generics.ListCreateAPIView):
    queryset = PerformanceGoal.objects.select_related("employee", "cycle")
    serializer_class = PerformanceGoalSerializer
    permission_classes = [permissions.IsAuthenticated]

class PerformanceGoalDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PerformanceGoal.objects.select_related("employee", "cycle")
    serializer_class = PerformanceGoalSerializer
    permission_classes = [permissions.IsAuthenticated]


class PerformanceEvaluationListCreateView(generics.ListCreateAPIView):
    serializer_class = PerformanceEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff: 
            return PerformanceEvaluation.objects.all()
        return PerformanceEvaluation.objects.filter(employee=user)

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user)

class SubmitForReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            evaluation = PerformanceEvaluation.objects.get(pk=pk)
        except PerformanceEvaluation.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if evaluation.employee != request.user:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        evaluation.status = "submitted"
        evaluation.save()
        return Response({"status": "submitted"}, status=status.HTTP_200_OK)

class AddFeedbackView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            evaluation = PerformanceEvaluation.objects.get(pk=pk)
        except PerformanceEvaluation.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.is_staff and evaluation.evaluator != request.user:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        evaluation.feedback = request.data.get("feedback", evaluation.feedback)
        evaluation.improvement_notes = request.data.get("improvement_notes", evaluation.improvement_notes)
        evaluation.rating = request.data.get("rating", evaluation.rating)
        evaluation.status = "reviewed"
        evaluation.save()

        return Response(
            {
                "status": "reviewed",
                "feedback": evaluation.feedback,
                "rating": evaluation.rating,
            },
            status=status.HTTP_200_OK,
        )
class PerformanceEvaluationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PerformanceEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = PerformanceEvaluation.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return PerformanceEvaluation.objects.all()
        return PerformanceEvaluation.objects.filter(employee=user)



class AttendanceRecordListCreateView(generics.ListCreateAPIView):
    queryset = AttendanceRecord.objects.select_related("employee")
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

class AttendanceRecordDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AttendanceRecord.objects.select_related("employee")
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]



class LeaveTypeListCreateView(generics.ListCreateAPIView):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

class LeaveTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        emp_id = self.request.query_params.get("employee")
        qs = LeaveBalance.objects.all()
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        return qs


class LeaveRequestListCreateView(generics.ListCreateAPIView):
    queryset = LeaveRequest.objects.select_related("employee", "leave_type", "manager")
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

class LeaveRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveRequest.objects.select_related("employee", "leave_type", "manager")
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


class LeaveRequestApproveView(generics.UpdateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        lr = self.get_object()
        approve_leave(lr, manager_user=request.user)
        return Response({"detail": "Approved"}, status=status.HTTP_200_OK)


class LeaveRequestRejectView(generics.UpdateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        lr = self.get_object()
        reject_leave(lr, manager_user=request.user)
        return Response({"detail": "Rejected"}, status=status.HTTP_200_OK)



class OvertimeRecordListCreateView(generics.ListCreateAPIView):
    queryset = OvertimeRecord.objects.select_related("employee")
    serializer_class = OvertimeRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

class OvertimeRecordDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OvertimeRecord.objects.select_related("employee")
    serializer_class = OvertimeRecordSerializer
    permission_classes = [permissions.IsAuthenticated]


class PayrollConfigListCreateView(generics.ListCreateAPIView):
    queryset = PayrollConfig.objects.all()
    serializer_class = PayrollConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

class PayrollConfigDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PayrollConfig.objects.all()
    serializer_class = PayrollConfigSerializer
    permission_classes = [permissions.IsAuthenticated]


class PayrollRunListCreateView(generics.ListCreateAPIView):
    queryset = PayrollRun.objects.all()
    serializer_class = PayrollRunSerializer
    permission_classes = [permissions.IsAuthenticated]

class PayrollRunDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PayrollRun.objects.all()
    serializer_class = PayrollRunSerializer
    permission_classes = [permissions.IsAuthenticated]


class GeneratePayrollRunView(generics.GenericAPIView):
    serializer_class = PayrollRunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ps = request.data.get("period_start")
        pe = request.data.get("period_end")
        period_start = datetime.strptime(ps, "%Y-%m-%d").date()
        period_end = datetime.strptime(pe, "%Y-%m-%d").date()
        run = generate_payroll_run(period_start, period_end, processed_by=request.user)
        return Response(PayrollRunSerializer(run).data, status=status.HTTP_201_CREATED)


class PayslipListView(generics.ListAPIView):
    queryset = Payslip.objects.select_related("employee", "payroll_run")
    serializer_class = PayslipSerializer
    permission_classes = [permissions.IsAuthenticated]

class PayslipDetailView(generics.RetrieveAPIView):
    queryset = Payslip.objects.select_related("employee", "payroll_run")
    serializer_class = PayslipSerializer
    permission_classes = [permissions.IsAuthenticated]



class ResourceAssignmentListCreateView(generics.ListCreateAPIView):
    queryset = ResourceAssignment.objects.select_related("employee__user", "project", "role")
    serializer_class = ResourceAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["employee", "project", "role", "is_primary"]
    ordering_fields = ["start_date", "end_date", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        active = self.request.query_params.get("active")
        if active:
            today = date.today()
            qs = qs.filter(start_date__lte=today, end_date__gte=today)
        s = self.request.query_params.get("from"); e = self.request.query_params.get("to")
        if s and e:
            S = datetime.strptime(s, "%Y-%m-%d").date()
            E = datetime.strptime(e, "%Y-%m-%d").date()
            qs = qs.filter(start_date__lte=E, end_date__gte=S)
        return qs


class ResourceAssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ResourceAssignment.objects.select_related("employee__user", "project", "role")
    serializer_class = ResourceAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProjectSkillRequirementListCreateView(generics.ListCreateAPIView):
    queryset = ProjectSkillRequirement.objects.select_related("project", "skill")
    serializer_class = ProjectSkillRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProjectSkillRequirementDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProjectSkillRequirement.objects.select_related("project", "skill")
    serializer_class = ProjectSkillRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]


class ResourceForecastListCreateView(generics.ListCreateAPIView):
    queryset = ResourceForecast.objects.select_related("project")
    serializer_class = ResourceForecastSerializer
    permission_classes = [permissions.IsAuthenticated]


class ResourceForecastDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ResourceForecast.objects.select_related("project")
    serializer_class = ResourceForecastSerializer
    permission_classes = [permissions.IsAuthenticated]


class UtilizationReportView(APIView):
    def get(self, request):
        emp_id = request.query_params.get("employee_id")
        week = request.query_params.get("week")  
        if not emp_id or not week:
            return Response({"error": "employee_id and week required"}, status=400)

        emp = Employee.objects.get(pk=emp_id)
        year, week_num = map(int, week.split("-"))
        week_start = date.fromisocalendar(year, week_num, 1)
        week_end = week_start + timedelta(days=6)

        record = UtilizationRecord.objects.filter(employee=emp, week_start=week_start).first()

        if record:
            hours, utilization = compute_utilization(emp, week_start, week_end)
            record.hours_logged = hours
            record.utilization_percent = utilization
            record.save(update_fields=["hours_logged", "utilization_percent"])
        else:
            hours, utilization = compute_utilization(emp, week_start, week_end)
            record = UtilizationRecord.objects.create(
                employee=emp, week_start=week_start,
                hours_logged=hours, utilization_percent=utilization
            )

        return Response({
            "employee": emp.name,
            "week_start": week_start,
            "hours_logged": record.hours_logged,
            "utilization_percent": record.utilization_percent,
        })


class CrossProjectSplitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee")
        s = request.query_params.get("start")
        e = request.query_params.get("end")
        start = datetime.strptime(s, "%Y-%m-%d").date()
        end = datetime.strptime(e, "%Y-%m-%d").date()
        data = project_time_split(employee_id, start, end)
        return Response(data)




class RecommendationView(APIView):
    """
    POST:
    {
      "project": "<uuid|int>",
      "start": "YYYY-MM-DD",
      "end": "YYYY-MM-DD",
      "requirements": [{"skill_id": "<uuid>", "min_level": 3}, ...],
      "limit": 10,

      // Optional (new):
      "weights": {
        "skill_coverage": 0.45,
        "skill_level_fit": 0.25,
        "free_capacity": 0.20,
        "utilization": 0.10
      },
      "desired_hours_per_week": 20,        // float/decimal
      "exclude_heavily_booked": true,      // bool
      "heavy_booking_threshold_percent": 90 // 0..100
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from decimal import Decimal
        project_id = request.data["project"]
        start = datetime.strptime(request.data["start"], "%Y-%m-%d").date()
        end = datetime.strptime(request.data["end"], "%Y-%m-%d").date()
        reqs = request.data.get("requirements", [])
        limit = int(request.data.get("limit", 10))

        weights = request.data.get("weights")
        desired = request.data.get("desired_hours_per_week")
        if desired is not None:
            try:
                desired = Decimal(str(desired))
            except Exception:
                desired = None

        exclude_heavy = bool(request.data.get("exclude_heavily_booked", False))
        heavy_thresh = request.data.get("heavy_booking_threshold_percent", 90)
        try:
            heavy_thresh = Decimal(str(heavy_thresh))
        except Exception:
            heavy_thresh = Decimal("90")

        data = recommend_employees(
            project_id,
            reqs,
            start,
            end,
            limit=limit,
            weights=weights,
            desired_hours_per_week=desired,
            exclude_heavily_booked=exclude_heavy,
            heavy_booking_threshold_percent=heavy_thresh,
        )
        return Response(data)

class CapacityPlanningView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project")
        s = request.query_params.get("start")
        e = request.query_params.get("end")
        start = datetime.strptime(s, "%Y-%m-%d").date()
        end = datetime.strptime(e, "%Y-%m-%d").date()
        data = forecast_gaps(project_id, start, end)
        return Response(data)