
import logging
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.utils import timezone
from django.db.models import Count

from .models import Invoice, Payment
from .utils import allocate_payment

logger = logging.getLogger(__name__)
DEFAULT_FROM = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")


#  Email sending 
# def send_invoice_email_with_attachment(invoice_id):
#     """Background task: generate invoice PDF and email to client."""
#     try:
#         inv = Invoice.objects.get(id=invoice_id)
#     except Invoice.DoesNotExist:
#         logger.warning("Invoice %s not found when trying to send email", invoice_id)
#         return

#     try:
#         inv.recalc_totals()
#         generate_and_attach_pdf(inv)

#         subject = f"Invoice #{inv.invoice_number}"
#         body = (
#             f"Hello {inv.client_name},\n\n"
#             f"Please find attached invoice #{inv.invoice_number}.\n"
#             f"Total: {inv.total_amount}\n"
#             f"Due: {inv.due_date}\n\n"
#             f"Thanks,\n{DEFAULT_FROM}"
#         )

#         email = EmailMessage(subject, body, DEFAULT_FROM, [inv.client_email])
#         if inv.pdf_file and getattr(inv.pdf_file, "path", None):
#             email.attach_file(inv.pdf_file.path)

#         email.send(fail_silently=False)
#         inv.mark_sent()
#         logger.info("Invoice %s emailed to %s", inv.invoice_number, inv.client_email)

#     except Exception:
#         logger.exception("Failed to send invoice %s", invoice_id)


def allocate_payment_task(payment_id):
    """Background task: allocate a payment to invoices/partners."""
    try:
        p = Payment.objects.get(id=payment_id)
        allocate_payment(p)
        logger.info("Allocated payment %s", payment_id)
    except Payment.DoesNotExist:
        logger.warning("Payment %s not found when trying to allocate", payment_id)
    except Exception:
        logger.exception("Error allocating payment %s", payment_id)


def run_invoice_reminder_jobs():
    """Send reminders for due invoices and mark overdue ones."""
    reminder_days = getattr(settings, "INVOICE_REMINDER_DAYS_BEFORE", [7, 3, 1])
    today = timezone.now().date()

    # Send reminders BEFORE due date
    for days in reminder_days:
        target_date = today + timezone.timedelta(days=days)
        qs = Invoice.objects.filter(
            due_date=target_date,
            status__in=[
                Invoice.Status.DRAFT,
                Invoice.Status.SENT,
                Invoice.Status.PARTIALLY_PAID,
            ],
        )
        for inv in qs.iterator():
            try:
                subject = f"Reminder: Invoice #{inv.invoice_number} due in {days} day(s)"
                body = (
                    f"Invoice #{inv.invoice_number} for {inv.client_name} "
                    f"is due on {inv.due_date}. Total: {inv.total_amount}"
                )
                send_mail(subject, body, DEFAULT_FROM, [inv.client_email], fail_silently=True)
                logger.info("Sent reminder for invoice %s to %s", inv.invoice_number, inv.client_email)
            except Exception:
                logger.exception("Failed to send reminder for invoice %s", inv.id)

    # Mark overdue and notify finance
    overdue_qs = Invoice.objects.filter(due_date__lt=today).exclude(status=Invoice.Status.PAID)
    finance_recipients = list(getattr(settings, "FINANCE_NOTIFICATION_EMAILS", []))
    for inv in overdue_qs.iterator():
        try:
            if inv.status != Invoice.Status.OVERDUE:
                inv.status = Invoice.Status.OVERDUE
                inv.save(update_fields=["status", "updated_at"])
            subject = f"Overdue: Invoice #{inv.invoice_number}"
            body = (
                f"Invoice #{inv.invoice_number} for {inv.client_name} "
                f"is overdue since {inv.due_date}. Total: {inv.total_amount}"
            )
            send_mail(subject, body, DEFAULT_FROM, [inv.client_email], fail_silently=True)
            if finance_recipients:
                send_mail(subject, body, DEFAULT_FROM, finance_recipients, fail_silently=True)
            logger.info("Overdue notification sent for invoice %s", inv.invoice_number)
        except Exception:
            logger.exception("Failed processing overdue invoice %s", inv.id)


def reconcile_allocations_for_unallocated_payments():
    """Try allocating all payments that don’t have allocations yet."""
    payments = Payment.objects.annotate(num_alloc=Count("allocations")).filter(num_alloc=0)
    for p in payments:
        try:
            allocate_payment(p)
            logger.info("Reconciled allocation for payment %s", p.id)
        except Exception:
            logger.exception("Allocation failed for payment %s", p.id)
