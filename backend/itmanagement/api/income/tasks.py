from background_task import background
from django.core.mail import EmailMessage, send_mail
from django.conf import settings
from django.utils import timezone
from .models import Invoice
from .utils import generate_invoice_pdf, recalc_invoice_totals
import os

DEFAULT_FROM = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

@background(schedule=0)
def send_invoice_email_with_attachment(invoice_id):
    inv = Invoice.objects.get(id=invoice_id)
    recalc_invoice_totals(inv)

    # Generate PDF
    pdf_path = generate_invoice_pdf(inv)

    subject = f"Invoice #{inv.id}"
    body = f"Hello {inv.client_name},\n\nPlease find attached invoice #{inv.id}.\nTotal: {inv.total_amount}\nDue: {inv.due_date}\n\nThanks."
    email = EmailMessage(subject, body, DEFAULT_FROM, [inv.client_email])

    try:
        email.attach_file(pdf_path)
        email.send(fail_silently=False)
        # Only mark as sent if email is successful
        inv.mark_sent()
    except Exception as e:
        # Optional: log error
        print(f"Failed to send invoice email: {e}")
    finally:
        # Delete temporary PDF file
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


@background(schedule=60)
def run_invoice_reminder_jobs():
    """
    Sends reminders: before due date and marks overdue after due date.
    """
    reminder_days = getattr(settings, "INVOICE_REMINDER_DAYS_BEFORE", [7, 3, 1])
    today = timezone.now().date()

    # reminders before due date
    for days in reminder_days:
        target = today + timezone.timedelta(days=days)
        for inv in Invoice.objects.filter(due_date=target, status__in=["draft", "sent"]).iterator():
            subject = f"Reminder: Invoice #{inv.id} due in {days} day(s)"
            body = f"Invoice #{inv.id} for {inv.client_name} is due on {inv.due_date}. Total: {inv.total_amount}"
            send_mail(subject, body, DEFAULT_FROM, [inv.client_email], fail_silently=True)

    # mark overdue and notify finance
    overdue_qs = Invoice.objects.filter(due_date__lt=today, status__in=["draft", "sent"])
    for inv in overdue_qs:
        inv.status = "overdue"
        inv.save(update_fields=["status"])
        recipients = list(getattr(settings, "FINANCE_NOTIFICATION_EMAILS", []))
        subject = f"Overdue: Invoice #{inv.id}"
        body = f"Invoice #{inv.id} for {inv.client_name} is overdue since {inv.due_date}. Total: {inv.total_amount}"
        if recipients:
            send_mail(subject, body, DEFAULT_FROM, recipients, fail_silently=True)


@shared_task
def send_invoice_reminders():
    today = timezone.now().date()
    invoices = Invoice.objects.filter(status__in=['sent', 'overdue'])

    for invoice in invoices:
        days_diff = (invoice.due_date - today).days

        if days_diff == 2:  # Reminder before due date
            send_mail(
                subject="Invoice Due Reminder",
                message=f"Your invoice #{invoice.id} is due in 2 days.",
                from_email="billing@example.com",
                recipient_list=[invoice.client_email],
            )
        elif days_diff < 0:  # Overdue reminder
            send_mail(
                subject="Invoice Overdue",
                message=f"Your invoice #{invoice.id} is overdue. Please make payment.",
                from_email="billing@example.com",
                recipient_list=[invoice.client_email],
            )