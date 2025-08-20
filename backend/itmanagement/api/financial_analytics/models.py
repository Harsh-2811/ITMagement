import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
TWOPLACES = Decimal("0.01")


class CostCenter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class FinancialPeriod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    start_date = models.DateField()
    end_date = models.DateField()
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ("start_date", "end_date")

    def __str__(self):
        return self.name


class BaseReport(models.Model):
    """
    Abstract base for all financial reports
    Adds versioning and finalization support.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period = models.ForeignKey(FinancialPeriod, on_delete=models.CASCADE)
    version = models.IntegerField(default=1)
    is_finalized = models.BooleanField(default=False)
    base_currency = models.CharField(max_length=10, default="INR")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        unique_together = ("period", "version")


class ProfitLossReport(BaseReport):
    total_income = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_expense = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    net_profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"P&L: {self.period.name} (v{self.version})"


class CashFlowReport(BaseReport):
    total_inflow = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_outflow = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    net_cash = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"Cash Flow: {self.period.name} (v{self.version})"


class PartnerFinancialBreakdown(BaseReport):
    partner = models.ForeignKey(User, on_delete=models.CASCADE)
    income = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    expense = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    net_profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta(BaseReport.Meta):
        unique_together = ("partner", "period", "version")

    def __str__(self):
        return f"{self.partner.username} | {self.period.name} (v{self.version})"


class TaxReport(BaseReport):
    total_taxable_income = models.DecimalField(max_digits=14, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2)
    tax_due = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    def calculate(self):
        incomes = self.period.invoices.aggregate(
            total=models.Sum("total_amount")
        )["total"] or Decimal("0.00")

        deductions = self.period.expenses.aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

        self.total_taxable_income = incomes
        self.total_deductions = deductions
        self.tax_due = (self.total_taxable_income - self.total_deductions) * (self.tax_rate / Decimal("100"))
        self.save()

    def __str__(self):
        return f"Tax Report: {self.period.name} (v{self.version})"



class ForecastReport(BaseReport):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period = models.ForeignKey(
        FinancialPeriod, on_delete=models.CASCADE, related_name="forecast_reports"
    )

    forecasted_income = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    forecasted_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    expected_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    net_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Forecast Report"
        verbose_name_plural = "Forecast Reports"

    def __str__(self):
        return f"Forecast Report for {self.period}"

    def calculate_forecast(self):
        """
        Calculate forecasted income, expenses, tax, and net profit for this period.
        """

        # Aggregate income & expenses (can be from planned or historical data)
        incomes = self.period.invoices.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
        expenses = self.period.expenses.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        self.forecasted_income = incomes
        self.forecasted_expenses = expenses

        # Example: Assume a flat 10% tax rate (customize if needed)
        self.expected_tax = (self.forecasted_income - self.forecasted_expenses) * Decimal("0.10") \
                            if self.forecasted_income > self.forecasted_expenses else Decimal("0.00")

        # Net Profit = Income - Expenses - Tax
        self.net_profit = self.forecasted_income - self.forecasted_expenses - self.expected_tax

        self.save()
        return self
