from decimal import Decimal
from django.db.models import Sum
from django.core.exceptions import ValidationError
from .models import Expense, ExpenseBudget, PartnerExpenseAllocation, ExpenseReport, ExpenseAuditLog, TWOPLACES
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

User = get_user_model()

def compute_partner_allocations(expense: Expense, ratios: dict):
    allocations = []
    total_ratio = sum(ratios.values())
    if total_ratio <= 0:
        raise ValidationError("Total allocation ratio must be > 0")
    for partner_id, ratio in ratios.items():
        amount = (expense.amount * Decimal(ratio / total_ratio)).quantize(TWOPLACES)
        allocations.append({"partner_id": partner_id, "amount": amount})
    total_allocated = sum([a["amount"] for a in allocations])
    diff = expense.amount - total_allocated
    if allocations and diff != 0:
        allocations[0]["amount"] += diff
    return allocations


def generate_expense_report(start_date, end_date, persist=True):
    categories = ExpenseBudget.objects.values_list("category", flat=True).distinct()
    reports = []
    for cat_id in categories:
        # Aggregate budget
        budget_agg = ExpenseBudget.objects.filter(
            category_id=cat_id,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).aggregate(total_budget=Sum("amount"))
        total_budget = budget_agg["total_budget"] or Decimal("0.00")

        # Aggregate approved expenses
        expense_agg = Expense.objects.filter(
            category_id=cat_id,
            status="Approved",
            created_at__gte=start_date,
            created_at__lte=end_date
        ).aggregate(total_expense=Sum("amount"))
        total_expense = expense_agg["total_expense"] or Decimal("0.00")

        over_budget = total_expense > total_budget
        percentage_used = (total_expense / total_budget * 100).quantize(TWOPLACES) if total_budget > 0 else Decimal("0.00")

        report_data = {
            "category_id": cat_id,
            "total_budget": total_budget,
            "total_expense": total_expense,
            "over_budget": over_budget,
            "percentage_used": percentage_used,
            "period_start": start_date,
            "period_end": end_date
        }

        if persist:
            ExpenseReport.objects.update_or_create(
                category_id=cat_id,
                period_start=start_date,
                period_end=end_date,
                defaults=report_data
            )

        reports.append(report_data)
    return reports


def notify_managers_new_expense(expense: Expense):
    managers = User.objects.filter(is_staff=True)
    emails = [m.email for m in managers if m.email]
    if emails:
        send_mail(
            subject=f"New Expense Submitted: {expense.title}",
            message=f"Expense '{expense.title}' of amount {expense.amount} has been submitted by {expense.submitted_by.username}.",
            from_email="no-reply@company.com",
            recipient_list=emails,
            fail_silently=True,
        )


def create_audit_log(expense: Expense, old_status: str, new_status: str, user, notes=""):
    ExpenseAuditLog.objects.create(
        expense=expense,
        old_status=old_status,
        new_status=new_status,
        changed_by=user,
        notes=notes
    )


def validate_expense_budget(expense: Expense):
    """Check if expense exceeds current budget."""
    start_date = expense.created_at.date()
    end_date = start_date
    budget = ExpenseBudget.objects.filter(
        category=expense.category,
        start_date__lte=end_date,
        end_date__gte=start_date
    ).aggregate(total_budget=Sum("amount"))["total_budget"] or Decimal("0.00")

    approved_expenses = Expense.objects.filter(
        category=expense.category,
        status="Approved"
    ).aggregate(total_expense=Sum("amount"))["total_expense"] or Decimal("0.00")

    if approved_expenses + expense.amount > budget:
        return True  # over budget
    return False
