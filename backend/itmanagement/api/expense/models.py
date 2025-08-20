import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from api.financial_analytics.models import CostCenter
from api.financial_analytics.models import FinancialPeriod
User = get_user_model()
TWOPLACES = Decimal("0.01")


class ExpenseCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name


class ExpenseBudget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name="budgets")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    class Meta:
        unique_together = ("category", "start_date", "end_date")
    def __str__(self):
        return f"{self.category.name} | {self.start_date} → {self.end_date}"


def validate_receipt(file):
    max_size = 5 * 1024 * 1024  # 5 MB
    allowed_types = ["application/pdf", "image/jpeg", "image/png"]
    if file.size > max_size:
        raise ValidationError("Receipt file size must be <= 5MB")
    if file.content_type not in allowed_types:
        raise ValidationError("Allowed file types: PDF, JPG, PNG")

class Expense(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, related_name="expenses")
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submitted_expenses")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_expenses")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    receipt = models.FileField(upload_to="expenses/receipts/", null=True, blank=True, validators=[validate_receipt])
    partners = models.ManyToManyField(User, through="PartnerExpenseAllocation", related_name="partner_expenses")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    period = models.ForeignKey(FinancialPeriod, on_delete=models.CASCADE, related_name="expenses", null=True, blank=True)

    def __str__(self):
        return f"{self.title} | {self.amount} | {self.status}"


class PartnerExpenseAllocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="allocations")
    partner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expense_allocations")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    class Meta:
        unique_together = ("expense", "partner")
    def __str__(self):
        return f"{self.partner.username} → {self.amount}"


class ExpenseReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True)
    total_budget = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_expense = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    percentage_used = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    over_budget = models.BooleanField(default=False)
    period_start = models.DateField()
    period_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.category.name} | {self.period_start} → {self.period_end} | OverBudget={self.over_budget}"


class ExpenseAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="audit_logs")
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"{self.expense.title} | {self.old_status} → {self.new_status}"
