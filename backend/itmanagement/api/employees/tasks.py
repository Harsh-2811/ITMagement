# hr/tasks.py
from datetime import date, timedelta
from django.core.mail import send_mail
from background_task import background
from .models import EmployeeContract, Certification, Employee
from .utils import generate_payroll_run

@background(schedule=0)
def notify_expiring_contracts(days=30):
    for c in EmployeeContract.objects.all():
        if c.end_date and (c.end_date - date.today()).days == days:
            send_mail(
                subject=f"Contract expiring in {days} days: {c.title}",
                message=f"Contract for {c.employee.user.get_full_name()} ends on {c.end_date}.",
                from_email=None,
                recipient_list=[c.employee.user.email],
                fail_silently=True
            )

@background(schedule=0)
def notify_expiring_certifications(days=30):
    for cert in Certification.objects.all():
        if cert.expiry_date and (cert.expiry_date - date.today()).days == days:
            send_mail(
                subject=f"Certification expiring in {days} days: {cert.name}",
                message=f"Certification for {cert.employee.user.get_full_name()} expires on {cert.expiry_date}.",
                from_email=None,
                recipient_list=[cert.employee.user.email],
                fail_silently=True
            )

@background(schedule=0)
def schedule_monthly_payroll(period_start_str, period_end_str, processed_by_id):
    from datetime import datetime
    ps = datetime.strptime(period_start_str, "%Y-%m-%d").date()
    pe = datetime.strptime(period_end_str, "%Y-%m-%d").date()
    from django.contrib.auth import get_user_model
    User = get_user_model()
    processed_by = User.objects.filter(id=processed_by_id).first()
    generate_payroll_run(ps, pe, processed_by)
