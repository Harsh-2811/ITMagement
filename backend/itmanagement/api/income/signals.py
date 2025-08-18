# invoices/signals.py
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings

from .models import InvoiceItem, Payment
from .utils import allocate_payment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=InvoiceItem)
@receiver(post_delete, sender=InvoiceItem)
def on_invoice_items_change(sender, instance, **kwargs):
    try:
        instance.invoice.recalc_totals()
    except Exception:
        logger.exception("Failed to recalc totals for invoice %s", getattr(instance, "invoice_id", None))


@receiver(post_save, sender=Payment)
def on_payment_created(sender, instance, created, **kwargs):
    """
    Recalc totals and allocate payment if created.
    Allocation may be done synchronously or scheduled depending on settings.INVOICE_ALLOCATE_ASYNC.
    """
    try:
        instance.invoice.recalc_totals()
    except Exception:
        logger.exception("Failed to recalc totals after payment %s", instance.id)

    if not created:
        return

    allocate_async = getattr(settings, "INVOICE_ALLOCATE_ASYNC", False)
    if allocate_async:
        try:
            from .tasks import allocate_payment_task
            allocate_payment_task(instance.id)
        except Exception:
            logger.exception("Failed to schedule allocate_payment_task for payment %s", instance.id)
    else:
        try:
            allocate_payment(instance)
        except Exception:
            logger.exception("Allocation error (signals) for payment %s", instance.id)
