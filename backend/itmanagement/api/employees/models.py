from django.db import models
import uuid
from decimal import Decimal
from datetime import date
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model

from api.users.models import User
from api.organizations.models import Organization
from api.projects.models import Project  

User = get_user_model()
TWOPLACES = Decimal("0.01")


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class JobRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=120, unique=True)
    level = models.CharField(max_length=50, blank=True, null=True)  # e.g., L1, L2, Senior
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.level or ''})"


class Employee(models.Model):
    PERMISSION_CHOICES = [
        ("all", "All Permissions"),
        ("limited", "Limited Permissions"),
        ("view_only", "View Only"),
    ]

    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"
        TERMINATED = "Terminated", "Terminated"
        ON_LEAVE = "On Leave", "On Leave"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee_profile")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="employees")
    employee_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100, blank=True, null=True)
    department = models.ForeignKey("Department", on_delete=models.SET_NULL, null=True, related_name="employees")
    role = models.ForeignKey(  
        "JobRole", on_delete=models.SET_NULL, null=True, blank=True, related_name="employees"
    )    
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="team_members")
    date_of_joining = models.DateField()
    date_of_exit = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    permissions = models.CharField(max_length=30, choices=PERMISSION_CHOICES, default="limited")
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="invited_employees")
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    alt_phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.JSONField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_full_name(self):
        return self.name or self.user.get_full_name() or self.user.username

    def promote(self, new_role: "JobRole", new_salary: Decimal | None = None):
        self.job_role = new_role
        if new_salary is not None:
            self.base_salary = Decimal(new_salary).quantize(Decimal("0.01"))
        self.save(update_fields=["role", "base_salary", "updated_at"])

    def __str__(self):
        return f"{self.get_full_name()} - {self.role} @ {self.organization.name}"


class EmployeeContract(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        EXPIRED = "Expired", "Expired"
        TERMINATED = "Terminated", "Terminated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="contracts")
    title = models.CharField(max_length=200)
    document = models.FileField(upload_to="employees/contracts/")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    auto_renew = models.BooleanField(default=False)
    renewal_terms = models.CharField(null=True, blank=True)
    weekly_hours = models.PositiveIntegerField(default=40)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_expired(self) -> bool:
        return date.today() > self.end_date

    def __str__(self):
        return f"{self.employee.employee_code} - {self.title}"


class EmployeeDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=100)
    file = models.FileField(upload_to="employee/documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    meta = models.CharField(null=True, blank=True)

    def __str__(self):
        return f"{self.doc_type} - {self.employee.employee_code}"


class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class EmployeeSkill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="employee_skills")
    level = models.PositiveSmallIntegerField(default=1)  # 1..5
    years = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("0.0"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("employee", "skill")

    def __str__(self):
        return f"{self.employee.employee_code} - {self.skill.name} ({self.level})"


class Certification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=200)
    authority = models.CharField(max_length=200, blank=True)
    certificate_file = models.FileField(upload_to="employees/certifications/", null=True, blank=True)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    meta = models.CharField(null=True, blank=True)

    def is_expired(self):
        return self.expiry_date and date.today() > self.expiry_date

    def __str__(self):
        return f"{self.name} - {self.employee.employee_code}"



class PerformanceCycle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name


class PerformanceGoal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="goals")
    cycle = models.ForeignKey(PerformanceCycle, on_delete=models.CASCADE, related_name="goals")
    title = models.CharField(max_length=200)
    kpi = models.CharField(max_length=200, blank=True)
    target_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    weight = models.PositiveSmallIntegerField(default=10)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.employee.employee_code} - {self.title}"


class PerformanceEvaluation(models.Model):
    class RatingScale(models.IntegerChoices):
        ONE = 1, "1 - Needs Improvement"
        TWO = 2, "2 - Below Expectations"
        THREE = 3, "3 - Meets Expectations"
        FOUR = 4, "4 - Exceeds Expectations"
        FIVE = 5, "5 - Outstanding"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="evaluations")
    cycle = models.ForeignKey(PerformanceCycle, on_delete=models.CASCADE, related_name="evaluations")
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="evaluations_done")
    overall_rating = models.IntegerField(choices=RatingScale.choices)
    rating = models.PositiveIntegerField(null=True, blank=True, help_text="Rating out of 10")
    feedback = models.TextField(blank=True, null=True, help_text="General feedback from evaluator")
    improvement_notes = models.TextField(blank=True, null=True, help_text="Areas for improvement")

    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("reviewed", "Reviewed"),
            ("completed", "Completed"),
        ],
        default="draft"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.cycle.name}"


class AttendanceRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    source = models.CharField(max_length=20, default="manual")
    note = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=[("P", "Present"), ("A", "Absent"), ("L", "Leave")])

    class Meta:
        unique_together = ("employee", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.date}"

class LeaveRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)

class LeaveType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=60, unique=True)
    accrual_per_month = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    carry_forward_limit = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    requires_approval = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("employee", "leave_type")

    def __str__(self):
        return f"{self.employee.employee_code} - {self.leave_type.name}: {self.balance}"


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"
        CANCELLED = "Cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="leave_approvals")
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def duration_days(self) -> Decimal:
        return Decimal((self.end_date - self.start_date).days + 1).quantize(TWOPLACES)

    def __str__(self):
        return f"{self.employee.employee_code} {self.leave_type.name} {self.start_date}→{self.end_date} {self.status}"

class BankDetail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="bank_detail")
    account_number = models.CharField(max_length=30)
    ifsc_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    branch_name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.bank_name}"
    

class Bonus(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="bonuses")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255)
    date = models.DateField(default=date.today)


class OvertimeRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="overtime")
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("1.50"))
    note = models.CharField(max_length=140, blank=True)

    class Meta:
        unique_together = ("employee", "date")


class PayrollConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    basic_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("40.00"))
    hra_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("20.00"))
    pf_employee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("12.00"))
    pf_employer_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("12.00"))
    esi_employee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.75"))
    esi_employer_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("3.25"))
    income_tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"))
    overtime_hour_rate = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("300.00"))


class PayrollRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period_start = models.DateField()
    period_end = models.DateField()
    processed_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note = models.TextField(blank=True, null=True)



class Payslip(models.Model):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        FINAL = "Final", "Final"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="payslips")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payslips")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    gross = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    basic = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    pf_employee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    esi_employee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    generated_at = models.DateTimeField(auto_now_add=True)

    line_items = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ("payroll_run", "employee")

    def __str__(self):
        return f"{self.employee.employee_code} - {self.payroll_run.period_start}→{self.payroll_run.period_end} - {self.net_pay}"


class ResourceAssignment(models.Model):
    """
    Employee assigned to a Project for a time window with a % allocation and planned hours/week.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="resource_assignments")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="resource_assignments")
    role = models.ForeignKey(JobRole, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    allocation_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("100.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    planned_hours_per_week = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("40.00"),
        validators=[MinValueValidator(0)]
    )
    is_primary = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # unique_together = ("employee", "project", "start_date", "end_date")
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["employee", "start_date", "end_date"]),
            models.Index(fields=["project", "start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} → {self.project.name} ({self.allocation_percent}%)"


class ProjectSkillRequirement(models.Model):
    """
    Skills needed for a project in a period (for matching & capacity planning).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="skill_requirements")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    min_level = models.PositiveSmallIntegerField(default=3)  # 1..5 like EmployeeSkill.level
    headcount = models.PositiveIntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField()
    weekly_hours_per_head = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("20.00"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["project", "skill__name", "start_date"]
        indexes = [
            models.Index(fields=["project", "skill", "start_date", "end_date"]),
        ]


class ResourceForecast(models.Model):
    """
    Capacity planning artifact: demand (required hours) for a project window by role or skill tag.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="resource_forecasts")
    label = models.CharField(max_length=120)  # e.g., "Backend Dev", "QA", "Designer"
    start_date = models.DateField()
    end_date = models.DateField()
    required_hours_per_week = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("40.00"))
    headcount = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [
            models.Index(fields=["project", "start_date", "end_date"]),
        ]

class UtilizationRecord(models.Model):
    """
    Cached utilization for a user over a period (optional snapshot).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="utilization_records")
    period_start = models.DateField()
    period_end = models.DateField()
    hours_logged = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    capacity_hours = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    utilization_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    computed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("employee", "period_start", "period_end")
        ordering = ["-period_start"]
        indexes = [
            models.Index(fields=["employee", "period_start", "period_end"]),
        ]