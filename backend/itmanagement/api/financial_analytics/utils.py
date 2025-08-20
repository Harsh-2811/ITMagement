from decimal import Decimal
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.http import Http404, StreamingHttpResponse
from django.conf import settings
from api.income.models import Invoice, PartnerIncomeShare
from api.expense.models import Expense, PartnerExpenseAllocation
from .models import (
    ProfitLossReport, CashFlowReport, PartnerFinancialBreakdown,
    TaxReport, FinancialPeriod, CostCenter, ForecastReport
)
import csv
import io

TWOPLACES = Decimal("0.01")
BASE_CURRENCY = getattr(settings, "FINANCE_BASE_CURRENCY", "INR")

def get_period_or_404(period_id):
    try:
        return FinancialPeriod.objects.get(id=period_id)
    except FinancialPeriod.DoesNotExist:
        raise Http404("Financial period not found.")

def _next_version(qs, period):
    last = qs.filter(period=period).order_by("-version").first()
    return (last.version + 1) if last else 1

def _create_version_or_reuse(model, period, defaults, force_new_version=False):
    """
    - If there is a non-finalized latest record, overwrite it (same version).
    - If finalized or force_new_version, create a new version = last + 1.
    """
    latest = model.objects.filter(period=period).order_by("-version").first()
    if latest and not latest.is_finalized and not force_new_version:
        # update in-place
        for k, v in defaults.items():
            setattr(latest, k, v)
        latest.base_currency = BASE_CURRENCY
        latest.save()
        return latest
    # create new version
    version = _next_version(model.objects, period)
    return model.objects.create(period=period, version=version, base_currency=BASE_CURRENCY, **defaults)

def _sum_invoices_base(period, extra_filter=None):
    qs = Invoice.objects.filter(
        status="paid",
        due_date__range=(period.start_date, period.end_date)
    )
    if extra_filter:
        qs = qs.filter(**extra_filter)

    # Normalize to base currency with exchange_rate snapshot on Invoice
    # Expect invoice has fields: total_amount, exchange_rate (rate to BASE)
    expr = ExpressionWrapper(F("total_amount") * F("exchange_rate"), output_field=DecimalField(max_digits=18, decimal_places=2))
    return qs.aggregate(total=Sum(expr))["total"] or Decimal("0.00")

def _sum_expenses_base(period, extra_filter=None):
    qs = Expense.objects.filter(
        status="Approved",
        created_at__range=(period.start_date, period.end_date)
    )
    if extra_filter:
        qs = qs.filter(**extra_filter)

    expr = F("amount")  # already base currency
    return qs.aggregate(total=Sum(expr))["total"] or Decimal("0.00")


def generate_profit_loss(period: FinancialPeriod, force_new_version=False):
    income = _sum_invoices_base(period)
    expense = _sum_expenses_base(period)
    net = (income - expense).quantize(TWOPLACES)
    return _create_version_or_reuse(
        ProfitLossReport,
        period,
        defaults={"total_income": income, "total_expense": expense, "net_profit": net},
        force_new_version=force_new_version
    )

def generate_cash_flow(period: FinancialPeriod, force_new_version=False):
    inflow = _sum_invoices_base(period)
    outflow = _sum_expenses_base(period)
    net = (inflow - outflow).quantize(TWOPLACES)
    return _create_version_or_reuse(
        CashFlowReport,
        period,
        defaults={"total_inflow": inflow, "total_outflow": outflow, "net_cash": net},
        force_new_version=force_new_version
    )

def generate_partner_breakdown(period: FinancialPeriod, force_new_version=False, restrict_partner_id=None):
    # income shares normalized
    shares = PartnerIncomeShare.objects.filter(
        invoice__status="paid",
        invoice__due_date__range=(period.start_date, period.end_date)
    )
    if restrict_partner_id:
        shares = shares.filter(partner_id=restrict_partner_id)

    # assume PartnerIncomeShare has 'amount' already in invoice currency; multiply by invoice.exchange_rate
    expr_income = ExpressionWrapper(F("amount") * F("invoice__exchange_rate"), output_field=DecimalField(max_digits=18, decimal_places=2))
    partner_summaries = shares.values("partner_id").annotate(total_income=Sum(expr_income))

    reports = []
    for summary in partner_summaries:
        partner_id = summary["partner_id"]
        income = summary["total_income"] or Decimal("0.00")
        allocs = PartnerExpenseAllocation.objects.filter(
            partner_id=partner_id,
            expense__status="Approved",
            expense__created_at__range=(period.start_date, period.end_date)
        )
        expr_exp = ExpressionWrapper(F("amount") * F("expense__exchange_rate"), output_field=DecimalField(max_digits=18, decimal_places=2))
        expense = allocs.aggregate(total=Sum(expr_exp))["total"] or Decimal("0.00")
        net = (income - expense).quantize(TWOPLACES)
        report = _create_version_or_reuse(
            PartnerFinancialBreakdown,
            period,
            defaults={"partner_id": partner_id, "income": income, "expense": expense, "net_profit": net},
            force_new_version=force_new_version
        )
        # ensure partner field kept if reusing existing
        if report.partner_id != partner_id:
            report.partner_id = partner_id
            report.save(update_fields=["partner"])
        reports.append(report)
    return reports

def generate_tax_report(period: FinancialPeriod, tax_rate: Decimal = Decimal("10"), force_new_version=False):
    total_income = _sum_invoices_base(period)
    total_deductions = _sum_expenses_base(period)
    taxable_income = (total_income - total_deductions).quantize(TWOPLACES)
    tax_due = (taxable_income * tax_rate / Decimal("100")).quantize(TWOPLACES)
    return _create_version_or_reuse(
        TaxReport,
        period,
        defaults={
            "total_taxable_income": taxable_income,
            "total_deductions": total_deductions,
            "tax_due": tax_due,
            "tax_rate": Decimal(tax_rate),
        },
        force_new_version=force_new_version
    )

def generate_cost_center_analysis(period: FinancialPeriod, limit_to_centers=None):
    centers = CostCenter.objects.all()
    if limit_to_centers:
        centers = centers.filter(name__in=limit_to_centers)

    analysis = []
    for center in centers:
        income = _sum_invoices_base(period, extra_filter={"cost_center": center})
        expense = _sum_expenses_base(period, extra_filter={"cost_center": center})
        net = (income - expense).quantize(TWOPLACES)
        analysis.append({
            "cost_center": center.name,
            "income": income,
            "expense": expense,
            "net_profit": net,
            "base_currency": BASE_CURRENCY
        })
    return analysis

def export_to_csv(queryset, fields, filename="report.csv"):
    """
    Streaming CSV for large datasets; converts Decimals to strings.
    """
    def row_iter():
        yield fields
        for obj in queryset.iterator():
            row = []
            for f in fields:
                val = getattr(obj, f)
                if isinstance(val, Decimal):
                    row.append(str(val))
                else:
                    row.append(str(val))
            yield row

    class Echo:
        def write(self, value):
            return value

    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    def stream():
        for row in row_iter():
            yield writer.writerow(row)

    response = StreamingHttpResponse(stream(), content_type="text/csv")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def generate_forecast(period: FinancialPeriod, periods_back=6, force_new_version=False):
    last_reports = ProfitLossReport.objects.order_by("-period__end_date")[:periods_back]
    if not last_reports.exists():
        return _create_version_or_reuse(
            ForecastReport,
            period,
            defaults={
                "forecasted_income": Decimal("0.00"),
                "forecasted_expense": Decimal("0.00"),
                "forecasted_net_profit": Decimal("0.00"),
            },
            force_new_version=force_new_version
        )

    last_reports = list(last_reports[::-1])  # oldest first
    weights = list(range(1, len(last_reports) + 1))
    total_weight = sum(weights) or 1

    weighted_income = sum([r.total_income * w for r, w in zip(last_reports, weights)]) / total_weight
    weighted_expense = sum([r.total_expense * w for r, w in zip(last_reports, weights)]) / total_weight

    forecasted_income = Decimal(weighted_income).quantize(TWOPLACES)
    forecasted_expense = Decimal(weighted_expense).quantize(TWOPLACES)
    forecasted_net = (forecasted_income - forecasted_expense).quantize(TWOPLACES)

    return _create_version_or_reuse(
        ForecastReport,
        period,
        defaults={
            "forecasted_income": forecasted_income,
            "forecasted_expense": forecasted_expense,
            "forecasted_net_profit": forecasted_net,
        },
        force_new_version=force_new_version
    )
