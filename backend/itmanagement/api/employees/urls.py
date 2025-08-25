from django.urls import path
from .views import EmployeeInviteView
from django.urls import path
from .views import *

urlpatterns = [
    path('invite/', EmployeeInviteView.as_view(), name='employee-invite'),

    path("departments/", DepartmentListCreateView.as_view()),
    path("departments/<uuid:pk>/", DepartmentDetailView.as_view()),
    path("roles/", JobRoleListCreateView.as_view()),
    path("roles/<uuid:pk>/", JobRoleDetailView.as_view()),


    path("employees/", EmployeeListCreateView.as_view()),
    path("employees/<uuid:pk>/", EmployeeDetailView.as_view()),
    path("contracts/", EmployeeContractListCreateView.as_view()),
    path("contracts/<uuid:pk>/", EmployeeContractDetailView.as_view()),
    path("documents/", EmployeeDocumentListCreateView.as_view()),
    path("documents/<uuid:pk>/", EmployeeDocumentDetailView.as_view()),


    path("skills/", SkillListCreateView.as_view()),
    path("skills/<uuid:pk>/", SkillDetailView.as_view()),
    path("employee-skills/", EmployeeSkillListCreateView.as_view()),
    path("employee-skills/<uuid:pk>/", EmployeeSkillDetailView.as_view()),
    path("certifications/", CertificationListCreateView.as_view()),
    path("certifications/<uuid:pk>/", CertificationDetailView.as_view()),


    path("perf-cycles/", PerformanceCycleListCreateView.as_view()),
    path("perf-cycles/<uuid:pk>/", PerformanceCycleDetailView.as_view()),
    path("goals/", PerformanceGoalListCreateView.as_view()),
    path("goals/<uuid:pk>/", PerformanceGoalDetailView.as_view()),
    path("evaluations/", PerformanceEvaluationListCreateView.as_view()),
    path("evaluations/<uuid:pk>/", PerformanceEvaluationDetailView.as_view()),
    path("evaluations/<int:pk>/submit/", SubmitForReviewView.as_view(), name="evaluation-submit"),
    path("evaluations/<int:pk>/feedback/", AddFeedbackView.as_view(), name="evaluation-feedback"),


    path("attendance/", AttendanceRecordListCreateView.as_view()),
    path("attendance/<uuid:pk>/", AttendanceRecordDetailView.as_view()),
    path("leave-types/", LeaveTypeListCreateView.as_view()),
    path("leave-types/<uuid:pk>/", LeaveTypeDetailView.as_view()),
    path("leave-balances/", LeaveBalanceListView.as_view()),
    path("leave-requests/", LeaveRequestListCreateView.as_view()),
    path("leave-requests/<uuid:pk>/", LeaveRequestDetailView.as_view()),
    path("leave-requests/<uuid:pk>/approve/", LeaveRequestApproveView.as_view()),
    path("leave-requests/<uuid:pk>/reject/", LeaveRequestRejectView.as_view()),


    path("overtime/", OvertimeRecordListCreateView.as_view()),
    path("overtime/<uuid:pk>/", OvertimeRecordDetailView.as_view()),
    path("payroll-config/", PayrollConfigListCreateView.as_view()),
    path("payroll-config/<uuid:pk>/", PayrollConfigDetailView.as_view()),
    path("payroll-runs/", PayrollRunListCreateView.as_view()),
    path("payroll-runs/<uuid:pk>/", PayrollRunDetailView.as_view()),
    path("payroll-runs/generate/", GeneratePayrollRunView.as_view()),
    path("payslips/", PayslipListView.as_view()),
    path("payslips/<uuid:pk>/", PayslipDetailView.as_view()),
    path("assignments/", ResourceAssignmentListCreateView.as_view(), name="resource-assignment-list-create"),
    path("assignments/<uuid:pk>/", ResourceAssignmentDetailView.as_view(), name="resource-assignment-detail"),
    path("requirements/", ProjectSkillRequirementListCreateView.as_view(), name="resource-req-list-create"),
    path("requirements/<uuid:pk>/", ProjectSkillRequirementDetailView.as_view(), name="resource-req-detail"),
    path("forecasts/", ResourceForecastListCreateView.as_view(), name="resource-forecast-list-create"),
    path("forecasts/<uuid:pk>/", ResourceForecastDetailView.as_view(), name="resource-forecast-detail"),


    path("utilization/", UtilizationReportView.as_view(), name="resource-utilization"),
    path("recommendations/", RecommendationView.as_view(), name="resource-recommendations"),
    path("cross-project-split/", CrossProjectSplitView.as_view(), name="resource-cross-split"),
    path("capacity/", CapacityPlanningView.as_view(), name="resource-capacity"),
]
