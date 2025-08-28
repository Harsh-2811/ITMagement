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



class EmployeeListCreateView(generics.ListCreateAPIView):
    queryset = Employee.objects.select_related("user", "department", "role")
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        return Response(
            self.get_serializer(employee).data,
            status=status.HTTP_201_CREATED
        )

class DepartmentListCreateView(generics.ListCreateAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED, 
        )

class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

class JobRoleListCreateView(generics.ListCreateAPIView):
    queryset = JobRole.objects.all()
    serializer_class = JobRoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

class JobRoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = JobRole.objects.all()
    serializer_class = JobRoleSerializer
    permission_classes = [permissions.IsAuthenticated]



class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Employee.objects.select_related("user", "department", "role")
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmployeeContractListCreateView(generics.ListCreateAPIView):
    queryset = EmployeeContract.objects.select_related("employee")
    serializer_class = EmployeeContractSerializer
    permission_classes = [permissions.IsAuthenticated]
    # parser_classes = [MultiPartParser, FormParser]

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
        serializer.save(manager=self.request.user)


class SubmitForReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            evaluation = PerformanceEvaluation.objects.get(pk=pk)
        except PerformanceEvaluation.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if evaluation.employee.user != request.user:
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

        if not request.user.is_staff and evaluation.manager != request.user:
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


class LeaveBalanceListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = LeaveBalance.objects.all()

        if not self.request.user.is_staff:
            qs = qs.filter(employee=self.request.user.employee_profile)

        emp_id = self.request.query_params.get("employee_id")
        if emp_id and self.request.user.is_staff:
            qs = qs.filter(employee_id=emp_id)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.user.is_staff:
            leave_balance = serializer.save()
        else:
            leave_balance = serializer.save(employee=request.user.employee_profile)

        return Response(
            self.get_serializer(leave_balance).data,
            status=status.HTTP_201_CREATED
        )


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
            return Response(
                {"error": "employee_id and week required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            emp = Employee.objects.get(pk=emp_id)
        except Employee.DoesNotExist:
            return Response(
                {"error": f"Employee with id {emp_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            year, week_num = map(int, week.split("-"))
            week_start = date.fromisocalendar(year, week_num, 1)  # Monday
            week_end = week_start + timedelta(days=6)             # Sunday
        except Exception:
            return Response(
                {"error": "week must be in YYYY-WW format, e.g. 2025-35"},
                status=status.HTTP_400_BAD_REQUEST
            )

        util_data = compute_utilization(emp.id, week_start, week_end)

        record, created = UtilizationRecord.objects.update_or_create(
            employee=emp,
            period_start=week_start,
            defaults={
                "period_end": week_end,
                "hours_logged": util_data["hours"],
                "utilization_percent": util_data["util_percent"],
            }
        )

        return Response({
            "employee_id": str(emp.id),
            "employee_name": str(emp),
            "week_start": week_start,
            "week_end": week_end,
            "hours_logged": util_data["hours"],
            "capacity_hours": util_data["capacity"],
            "utilization_percent": util_data["util_percent"],
            "record_created": created,
        })


class CrossProjectSplitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee")
        s = request.query_params.get("start")
        e = request.query_params.get("end")

        if not employee_id or not s or not e:
            return Response(
                {"error": "Query params 'employee', 'start', and 'end' are required"},
                status=400,
            )

        try:
            start = datetime.strptime(s.strip(), "%Y-%m-%d").date()
            end = datetime.strptime(e.strip(), "%Y-%m-%d").date()
        except Exception as ex:
            return Response(
                {
                    "error": "Invalid date format. Use YYYY-MM-DD.",
                    "received": {"start": s, "end": e, "exception": str(ex)},
                },
                status=400,
            )

        data = project_time_split(employee_id, start, end)
        return Response(data)




class RecommendationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from decimal import Decimal

        project_id = request.data.get("project")
        start_str = request.data.get("start")
        end_str = request.data.get("end")

        if not project_id or not start_str or not end_str:
            return Response(
                {"error": "Fields 'project', 'start', and 'end' are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

    def parse_date(self, value: str):
        """Try multiple date formats (YYYY-MM-DD or ISO8601)"""
        if not value:
            raise ValueError("Date value is missing")

        value = value.strip()
        try:
            # Strict YYYY-MM-DD
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            try:
                # ISO 8601 with optional Z
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except Exception:
                raise ValueError(f"Invalid date format received: '{value}'")

    def get(self, request):
        project_id = request.query_params.get("project")   # ✅ match your URL
        s = request.query_params.get("start")
        e = request.query_params.get("end")

        # Debugging: log exactly what values we got
        print("DEBUG project:", repr(project_id))
        print("DEBUG start:", repr(s))
        print("DEBUG end:", repr(e))

        if not s or not e:
            return Response(
                {"error": "Both 'start' and 'end' query parameters are required (YYYY-MM-DD or ISO 8601)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start = self.parse_date(s)
            end = self.parse_date(e)
        except ValueError as ex:
            return Response({"error": str(ex)}, status=status.HTTP_400_BAD_REQUEST)

        # Call your business logic
        data = forecast_gaps(project_id, start, end)
        return Response(data)
