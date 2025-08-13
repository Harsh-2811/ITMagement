from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

from api.users.models import User
from api.organizations.models import Organization
from api.partners.models import Partner


class TaxRule(models.Model):
    """
    Country-wise tax rules (e.g., VAT/GST).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country = models.CharField(max_length=100)
    tax_name = models.CharField(max_length=100, default="VAT")
    rate_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("country", "tax_name")

    def __str__(self):
        return f"{self.tax_name} {self.rate_percentage}% ({self.country})"


class RevenueCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="revenue_categories")
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    STATUS = (
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invoices")
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField()
    country = models.CharField(max_length=100)  # used to auto-pick TaxRule
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS, default="draft")

    tax_rule = models.ForeignKey(TaxRule, on_delete=models.SET_NULL, null=True, blank=True)

    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_invoices")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.id} — {self.client_name} ({self.status})"


class InvoiceItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    revenue_category = models.ForeignKey(
        RevenueCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice_items"
    )

    def line_total(self) -> Decimal:
        return (Decimal(self.quantity) * Decimal(self.unit_price)).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.description} ({self.quantity} x {self.unit_price})"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    method = models.CharField(max_length=50, blank=True, default="")
    reference = models.CharField(max_length=100, blank=True, default="")
    paid_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.amount} for {self.invoice_id}"


class PartnerIncomeShare(models.Model):
    """
    Define the intended share on an invoice for each partner.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="income_shares")
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="partner_shares")
    percentage = models.DecimalField(max_digits=5, decimal_places=2,
                                     validators=[MinValueValidator(0), MaxValueValidator(100)])
    # snapshot of computed amount (optional, updated on payment or recalc)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("partner", "invoice")

    def __str__(self):
        return f"{self.partner.user.username} — {self.percentage}% on {self.invoice_id}"


class PartnerAllocation(models.Model):
    """
    Allocation per Payment to each Partner (actuals).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="allocations")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.partner.user.username} <- {self.amount} (payment {self.payment_id})"