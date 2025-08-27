from rest_framework import serializers
from api.users.models import User
from .models import*

class EmployeeInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(required=False)
    # role = serializers.ChoiceField(choices=Employee.ROLE_CHOICES)
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
        u = obj.user
        return {
            "email": u.email,
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "phone": getattr(u, "phone", None),
            "is_verified": getattr(u, "is_verified", False),
        }

    def get_invited_by_name(self, obj):
        return f"{obj.invited_by.first_name} {obj.invited_by.last_name}" if obj.invited_by else None




class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class JobRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRole
        fields = "__all__"

class BankDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetail
        fields = ["account_number", "ifsc_code", "bank_name"]

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


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = "__all__"


class EmployeeSkillSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.get_full_name", read_only=True)
    skill_name = serializers.CharField(source="skill.name", read_only=True)

    class Meta:
        model = EmployeeSkill
        fields = "__all__"
        read_only_fields = ["updated_at"]


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = "__all__"



class PerformanceCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceCycle
        fields = "__all__"


class PerformanceGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceGoal
        fields = "__all__"


class PerformanceEvaluationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.get_full_name", read_only=True)
    manager_name = serializers.CharField(source="manager.get_full_name", read_only=True)

    class Meta:
        model = PerformanceEvaluation
        fields = [
            "id", "employee", "employee_name", "cycle",
            "manager", "manager_name",
            "overall_rating", "rating", "feedback", "improvement_notes",
            "status", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]



class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = "__all__"


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta: model = LeaveType; fields = "__all__"

class LeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRecord
        fields = "__all__"

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
            raise serializers.ValidationError("End date must be after start date")

        employee = data["employee"]
        start, end = data["start_date"], data["end_date"]
        allocation = data.get("allocation_percent", 0)

        overlapping = ResourceAssignment.objects.filter(
            employee=employee,
            start_date__lte=end,
            end_date__gte=start
        ).exclude(pk=self.instance.pk if self.instance else None)

        total_alloc = sum(a.allocation_percent for a in overlapping) + allocation
        if total_alloc > 100:
            raise serializers.ValidationError(
                f"Allocation exceeds 100% ({total_alloc}%) for employee {employee.name}"
            )

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