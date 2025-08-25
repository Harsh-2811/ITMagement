
import io
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from weasyprint import HTML
from django.conf import settings
from django.utils import timezone
import logging
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Sum, F
from .models import TaxRule, TaxRecord , PartnerAllocation , Invoice
from django.db.models import Max


logger = logging.getLogger(__name__)



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



TWOPLACES = Decimal("0.01")

def q2(v) -> Decimal:
    return (v if isinstance(v, Decimal) else Decimal(str(v))).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def active_rule_for_country(country: str):
    if not country:
        return None
    return (
        TaxRule.objects
        .filter(country__iexact=country, active=True)
        .order_by("-precedence", "-updated_at")
        .first()
    )


@transaction.atomic
def compute_and_store_tax(invoice, *, rule: TaxRule | None = None,
                          country_fallback_fields=("country", "client_country"),
                          metadata: dict | None = None) -> TaxRecord:

    # lock row to avoid race condition on versioning
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)

    # choose rule if absent
    if rule is None:
        country = None
        for field in country_fallback_fields:
            if hasattr(invoice, field):
                country = getattr(invoice, field) or country
        rule = active_rule_for_country(country)

    # subtotal from items
    subtotal = Decimal("0.00")
    for it in invoice.items.all():
        qty = Decimal(getattr(it, "quantity", 1))
        unit_price = Decimal(getattr(it, "unit_price", getattr(it, "price", "0.00")))
        subtotal += qty * unit_price
    subtotal = q2(subtotal)

    if rule is None:
        tax_amount = Decimal("0.00")
        total = subtotal
        breakdown = {}
    else:
        rate = Decimal(rule.rate_percentage)
        if rule.components:
            breakdown = {}
            total_component = Decimal("0.00")
            for k, v in rule.components.items():
                comp_rate = Decimal(str(v))
                comp_tax = q2(subtotal * comp_rate / Decimal("100"))
                breakdown[k] = str(comp_tax)  # ✅ store as string
                total_component += comp_tax
            tax_amount = q2(total_component)
        else:
            tax_amount = q2(subtotal * rate / Decimal("100"))
            breakdown = {"tax": str(tax_amount)}
        total = q2(subtotal + tax_amount)

    # update invoice snapshot
    invoice.subtotal_amount = subtotal
    invoice.tax_amount = tax_amount
    invoice.total_amount = total
    invoice.save(update_fields=["subtotal_amount", "tax_amount", "total_amount"])

    # deactivate old records
    TaxRecord.objects.filter(invoice=invoice, is_active=True).update(is_active=False)

    # next version
    last_version = (
        TaxRecord.objects.filter(invoice=invoice)
        .aggregate(Max("version"))
        .get("version__max") or 0
    )
    new_version = last_version + 1

    # create new record
    tr = TaxRecord.objects.create(
        invoice=invoice,
        tax_rule=rule,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total,
        breakdown=breakdown or None,
        metadata=metadata or None,
        version=new_version,
        is_active=True,
    )
    return tr

def reporting_aggregate(*, start=None, end=None, organization_id=None):
    from income.models import Invoice, InvoiceItem

    tr_qs = TaxRecord.objects.select_related("invoice", "tax_rule")
    def with_date_filters(qs):
        date_field = "invoice__issue_date" if hasattr(Invoice, "issue_date") else "invoice__created_at"
        if start:
            qs = qs.filter(**{f"{date_field}__gte": start})
        if end:
            qs = qs.filter(**{f"{date_field}__lte": end})
        return qs

    tr_qs = with_date_filters(tr_qs)
    if organization_id:
        tr_qs = tr_qs.filter(invoice__organization_id=organization_id)

    totals = tr_qs.aggregate(
        total_invoiced=Sum("total"),
        total_tax=Sum("tax_amount"),
        subtotal=Sum("subtotal"),
    )
    total_invoiced = totals["total_invoiced"] or Decimal("0.00")
    total_tax = totals["total_tax"] or Decimal("0.00")
    subtotal_sum = totals["subtotal"] or Decimal("0.00")

    # Client-wise
    client_map = {}
    for rec in tr_qs:
        client = getattr(rec.invoice, "client_name", "UNKNOWN")
        if client not in client_map:
            client_map[client] = {"invoiced": Decimal("0.00"), "tax": Decimal("0.00")}
        client_map[client]["invoiced"] += rec.total
        client_map[client]["tax"] += rec.tax_amount

    client_list = [
        {"client_name": c, "invoiced": str(q2(v["invoiced"])), "tax": str(q2(v["tax"]))}
        for c, v in client_map.items()
    ]

    # Category-wise
    item_qs = with_date_filters(InvoiceItem.objects.select_related("invoice", "revenue_category"))
    if organization_id:
        item_qs = item_qs.filter(invoice__organization_id=organization_id)

    cat_map = {}
    for it in item_qs:
        cat = getattr(it, "revenue_category", None)
        key = (getattr(cat, "id", None), getattr(cat, "name", "Uncategorized"))
        if key not in cat_map:
            cat_map[key] = {"invoiced": Decimal("0.00"), "tax": Decimal("0.00")}
        line = q2(Decimal(getattr(it, "quantity", 1)) * Decimal(getattr(it, "unit_price", getattr(it, "price", "0.00"))))
        cat_map[key]["invoiced"] += line

        inv_tr = it.invoice.active_tax_record()
        if inv_tr and inv_tr.subtotal > 0:
            prop = q2(line / inv_tr.subtotal)
            cat_map[key]["tax"] += q2(inv_tr.tax_amount * prop)

    category_list = [
        {"category_id": k[0], "category_name": k[1], "invoiced": str(q2(v["invoiced"])), "tax": str(q2(v["tax"]))}
        for k, v in cat_map.items()
    ]

    return {
        "period": {"start": str(start) if start else None, "end": str(end) if end else None},
        "organization_id": organization_id,
        "totals": {
            "subtotal": str(q2(subtotal_sum)),
            "tax": str(q2(total_tax)),
            "invoiced": str(q2(total_invoiced)),
        },
        "by_client": client_list,
        "by_category": category_list,
    }
