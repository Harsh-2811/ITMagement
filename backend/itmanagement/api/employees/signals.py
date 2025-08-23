from django.dispatch import receiver
from .models import LeaveRequest, LeaveBalance, Employee, EmployeeContract
from .utils import approve_leave
from api.dailytask.models import TaskTimeLog
from .models import ResourceAssignment, UtilizationRecord
from .utils import compute_utilization
from datetime import date, timedelta
from django.db.models.signals import post_save, post_delete , pre_save
@receiver(post_save, sender=Employee)
def create_default_leave_balances(sender, instance, created, **kwargs):
    if created:
        # Create default balances for all leave types when employee is onboarded
        from .models import LeaveType
        for lt in LeaveType.objects.all():
            LeaveBalance.objects.get_or_create(employee=instance, leave_type=lt)

@receiver(post_save, sender=LeaveRequest)
def auto_approve_if_not_required(sender, instance, created, **kwargs):
    # If a leave type doesn't require approval, auto-approve and deduct
    if created and not instance.leave_type.requires_approval:
        approve_leave(instance, manager_user=None)

@receiver(post_save, sender=EmployeeContract)
def mark_contract_status_on_save(sender, instance, **kwargs):
    if instance.is_expired and instance.status != instance.Status.EXPIRED:
        instance.status = instance.Status.EXPIRED
        instance.save(update_fields=["status"])

def current_week_range():
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


@receiver([post_save, post_delete], sender=TaskTimeLog)
def refresh_util_on_timelog_change(sender, instance, **kwargs):
    """
    Lightweight example: update current-week cached UtilizationRecord for that employee.
    """
    if not instance.user_id:
        return
    from .models import Employee
    emp = Employee.objects.filter(user_id=instance.user_id).first()
    if not emp:
        return
    start, end = current_week_range()
    metrics = compute_utilization(emp.id, start, end)
    UtilizationRecord.objects.update_or_create(
        employee=emp, period_start=start, period_end=end,
        defaults={
            "hours_logged": metrics["hours"],
            "capacity_hours": metrics["capacity"],
            "utilization_percent": metrics["util_percent"],
        }
    )


@receiver([post_save, post_delete], sender=ResourceAssignment)
def refresh_util_on_assignment_change(sender, instance, **kwargs):
    """
    Also refresh weekly cache when assignments change.
    """
    start, end = current_week_range()
    m = compute_utilization(instance.employee_id, start, end)
    UtilizationRecord.objects.update_or_create(
        employee_id=instance.employee_id, period_start=start, period_end=end,
        defaults={
            "hours_logged": m["hours"],
            "capacity_hours": m["capacity"],
            "utilization_percent": m["util_percent"],
        }
    )

@receiver(pre_save, sender=EmployeeContract)
def set_contract_status(sender, instance, **kwargs):
    if instance.is_expired:
        instance.status = instance.Status.EXPIRED