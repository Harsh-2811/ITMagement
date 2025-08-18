# invoices/utils.py
import io
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from weasyprint import HTML
from django.conf import settings
from django.utils import timezone
import logging

from .models import PartnerAllocation

logger = logging.getLogger(__name__)


def render_invoice_html(invoice):
    return render_to_string("invoice/invoice.html", {"invoice": invoice, "settings": settings})


def generate_invoice_pdf_bytes(invoice):
    html = render_invoice_html(invoice)
    pdf_file = io.BytesIO()
    HTML(string=html).write_pdf(pdf_file)
    pdf_file.seek(0)
    return pdf_file.read()


def generate_and_attach_pdf(invoice):
    """
    Generate PDF and attach to invoice.pdf_file.
    Returns saved file path or None.
    """
    try:
        invoice.recalc_totals()
        pdf_bytes = generate_invoice_pdf_bytes(invoice)
        filename = f"invoice_{invoice.invoice_number}.pdf"
        # use FileField.save which expects ContentFile; using unique name
        invoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        logger.info("Generated PDF for invoice %s", invoice.invoice_number)
        return invoice.pdf_file.path if invoice.pdf_file else None
    except Exception as exc:
        logger.exception("Failed to generate PDF for invoice %s: %s", getattr(invoice, "id", "?"), exc)
        return None


def allocate_payment(payment):
    """
    Allocate a Payment to partners according to invoice or org partner shares.
    Returns list of PartnerAllocation objects created.
    """
    from decimal import Decimal, ROUND_HALF_UP
    invoice = payment.invoice

    allocation_rules = invoice.partner_shares.all().order_by("priority")
    if not allocation_rules.exists():
        allocation_rules = invoice.organization.partner_shares.all().order_by("priority")

    remaining = Decimal(payment.amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    allocations = []
    logger.debug("Allocating payment %s for invoice %s amount=%s", payment.id, invoice.invoice_number, payment.amount)

    # First pass: calculate shares
    for rule in allocation_rules:
        if remaining <= Decimal("0.00"):
            break

        if rule.share_type == "fixed":
            share_amount = Decimal(rule.share_value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            share_amount = min(share_amount, remaining)
        else:  # percentage
            pct = (Decimal(rule.share_value) / Decimal("100.00"))
            raw = (Decimal(payment.amount) * pct)
            share_amount = raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            share_amount = min(share_amount, remaining)

        if share_amount <= Decimal("0.00"):
            continue

        pa = PartnerAllocation.objects.create(payment=payment, partner=rule.partner, amount=share_amount)
        allocations.append(pa)
        remaining -= share_amount

    # Assign remainder to fallback partner if any (to avoid unallocated cents)
    if remaining > Decimal("0.00"):
        fallback = None
        try:
            fallback = invoice.organization.partner_shares.first().partner if invoice.organization.partner_shares.exists() else None
        except Exception:
            fallback = None

        if not fallback:
            first_rule = (invoice.partner_shares.first() or invoice.organization.partner_shares.first())
            fallback = getattr(first_rule, "partner", None)

        if fallback:
            pa = PartnerAllocation.objects.create(payment=payment, partner=fallback, amount=remaining)
            allocations.append(pa)
            remaining = Decimal("0.00")
            logger.debug("Assigned remainder to fallback partner %s", fallback.pk)
        else:
            logger.warning("Payment %s left %s unallocated", payment.id, remaining)

    logger.info("Created %d allocations for payment %s", len(allocations), payment.id)
    return allocations
