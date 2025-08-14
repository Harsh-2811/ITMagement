from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Invoice, InvoiceItem, Payment, PartnerIncomeShare
from .utils import get_country_tax_rule, recalc_invoice_totals
from .tasks import send_invoice_email_with_attachment, run_invoice_reminder_jobs


@receiver(post_save, sender=InvoiceItem)
@receiver(post_delete, sender=InvoiceItem)
def on_invoice_items_change(sender, instance, **kwargs):
    recalc_invoice_totals(instance.invoice)


@receiver(post_save, sender=Invoice)
def on_invoice_save(sender, instance: Invoice, created, **kwargs):
    # Auto-attach tax rule by country if not set
    if instance.tax_rule is None and instance.country:
        rule = get_country_tax_rule(instance.country)
        if rule:
            instance.tax_rule = rule
            instance.save(update_fields=["tax_rule"])

    # Recalc totals on create/update
    recalc_invoice_totals(instance)

    # Kick reminder worker (or schedule via cron in prod)
    run_invoice_reminder_jobs(schedule=0)

    # If invoice already 'sent', ensure email goes out
    if instance.status == "sent":
        send_invoice_email_with_attachment(instance.id, schedule=0)


@receiver(post_save, sender=Payment)
def on_payment_save(sender, instance: Payment, created, **kwargs):
    if not created:
        return
    # After payment, recompute totals and possibly flip to paid
    inv = instance.invoice
    recalc_invoice_totals(inv)
