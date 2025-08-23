from rest_framework import serializers
from api.users.models import User
from .models import (
    Employee , ResourceAssignment, ProjectSkillRequirement, ResourceForecast, UtilizationRecord,
    Department, JobRole, Employee, EmployeeContract, EmployeeDocument,
    Skill, EmployeeSkill, Certification, PerformanceCycle, PerformanceGoal, PerformanceEvaluation,
    AttendanceRecord, LeaveType, LeaveBalance, LeaveRequest,
    OvertimeRecord, PayrollConfig, PayrollRun, Payslip , ResourceAssignment, ProjectSkillRequirement, ResourceForecast, UtilizationRecord

)
class EmployeeInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(required=False)
    role = serializers.ChoiceField(choices=Employee.ROLE_CHOICES)
    permissions = serializers.ChoiceField(choices=Employee.PERMISSION_CHOICES)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

class EmployeeDetailSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    invited_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = '__all__'

    def get_user(self, obj):
        return {
            "email": obj.user.email,
            "username": obj.user.username,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
            "phone": obj.user.phone,
            "is_verified": obj.user.is_verified,
        }

    def get_invited_by_name(self, obj):
        return f"{obj.invited_by.first_name} {obj.invited_by.last_name}" if obj.invited_by else None



# --- Catalog ---
class DepartmentSerializer(serializers.ModelSerializer):
    class Meta: model = Department; fields = "__all__"

class JobRoleSerializer(serializers.ModelSerializer):
    class Meta: model = JobRole; fields = "__all__"


# --- Employee & docs ---
class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

class EmployeeContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeContract
        fields = "__all__"

class EmployeeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocument
        fields = "__all__"


# --- Skills & certs ---
class SkillSerializer(serializers.ModelSerializer):
    class Meta: model = Skill; fields = "__all__"

class EmployeeSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSkill
        fields = "__all__"
        read_only_fields = ["updated_at"]

class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = "__all__"


# --- Performance ---
class PerformanceCycleSerializer(serializers.ModelSerializer):
    class Meta: model = PerformanceCycle; fields = "__all__"

class PerformanceGoalSerializer(serializers.ModelSerializer):
    class Meta: model = PerformanceGoal; fields = "__all__"

class PerformanceEvaluationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.get_full_name", read_only=True)
    evaluator_name = serializers.CharField(source="evaluator.get_full_name", read_only=True)

    class Meta:
        model = PerformanceEvaluation
        fields = [
            "id", "employee", "employee_name", "evaluator", "evaluator_name",
            "evaluation_period", "goals", "progress",
            "rating", "feedback", "improvement_notes",
            "status", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# --- Attendance & leave ---
class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = "__all__"

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta: model = LeaveType; fields = "__all__"

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = "__all__"
        read_only_fields = ["updated_at"]

class LeaveRequestSerializer(serializers.ModelSerializer):
    duration = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = ["requested_at", "decided_at"]

    def get_duration(self, obj): return float(obj.duration_days())


# --- Payroll ---
class OvertimeRecordSerializer(serializers.ModelSerializer):
    class Meta: model = OvertimeRecord; fields = "__all__"

class PayrollConfigSerializer(serializers.ModelSerializer):
    class Meta: model = PayrollConfig; fields = "__all__"

class PayrollRunSerializer(serializers.ModelSerializer):
    class Meta: model = PayrollRun; fields = "__all__"

class PayslipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payslip
        fields = "__all__"
        read_only_fields = ["generated_at", "line_items"]


class ResourceAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceAssignment
        fields = "__all__"

    def validate(self, data):
        if data["end_date"] < data["start_date"]:
            raise serializers.ValidationError("end_date must be >= start_date")
        return data


class ProjectSkillRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSkillRequirement
        fields = "__all__"

    def validate(self, data):
        if data["end_date"] < data["start_date"]:
            raise serializers.ValidationError("end_date must be >= start_date")
        return data


class ResourceForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceForecast
        fields = "__all__"

    def validate(self, data):
        if data["end_date"] < data["start_date"]:
            raise serializers.ValidationError("end_date must be >= start_date")
        return data


class UtilizationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UtilizationRecord
        fields = "__all__"
        read_only_fields = ["computed_at"]