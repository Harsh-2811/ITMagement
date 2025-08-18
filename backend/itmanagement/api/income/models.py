# invoices/models.py
import uuid
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator, EmailValidator
from django.conf import settings

from api.partners.models import Partner  # ensure import path
from api.organizations.models import Organization

AUTH_USER_MODEL = settings.AUTH_USER_MODEL


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"

    invoice_number = models.CharField(max_length=64, unique=True, editable=False)
    owner = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invoices")

    client_name = models.CharField(max_length=255)
    client_email = models.EmailField(validators=[EmailValidator()])
    client_country = models.CharField(max_length=100, default="India")
    client_state = models.CharField(max_length=100, blank=True, default="")

    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    currency = models.CharField(max_length=8, default="INR")
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("1.0000"))

    subtotal_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    pdf_file = models.FileField(upload_to="invoices/", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.invoice_number} - {self.client_name}"

    def _tax_rate(self):
        TAX_RATES = {
            "india": {"default": Decimal("18.00"), "gujarat": Decimal("12.00")},
            "usa": {"default": Decimal("8.50")},
        }
        country = (self.client_country or "").strip().lower()
        state = (self.client_state or "").strip().lower()
        if country in TAX_RATES:
            return TAX_RATES[country].get(state, TAX_RATES[country]["default"])
        return Decimal("0.00")

    def recalc_totals(self, save: bool = True):
        subtotal = Decimal("0.00")
        for it in self.items.all():
            subtotal += it.total_price()

        subtotal = subtotal.quantize(Decimal("0.01"))
        tax_rate = self._tax_rate()
        tax_amount = (subtotal * (tax_rate / Decimal("100.00"))).quantize(Decimal("0.01"))
        total = (subtotal + tax_amount).quantize(Decimal("0.01"))

        self.subtotal_amount = subtotal
        self.tax_amount = tax_amount
        self.total_amount = total

        # mark overdue if past due and not paid
        if self.status != self.Status.PAID and self.due_date and self.due_date < timezone.now().date():
            self.status = self.Status.OVERDUE

        if save:
            self.save(update_fields=["subtotal_amount", "tax_amount", "total_amount", "status", "updated_at"])

    @transaction.atomic
    def record_payment(self, amount: Decimal, method: str = "", reference: str = ""):
        if Decimal(amount) <= 0:
            raise ValueError("Payment amount must be positive.")

        p = Payment.objects.create(invoice=self, amount=amount, method=method or "", reference=reference or "")

        new_paid = (self.paid_amount + Decimal(amount)).quantize(Decimal("0.01"))
        self.paid_amount = new_paid

        if self.paid_amount >= self.total_amount:
            self.status = self.Status.PAID
            self.paid_at = timezone.now()
        elif self.paid_amount > Decimal("0.00"):
            self.status = self.Status.PARTIALLY_PAID

        self.save(update_fields=["paid_amount", "status", "paid_at", "updated_at"])

        InvoiceAuditLog.objects.create(
            invoice=self, action="payment", details=f"Recorded payment {amount} {self.currency} (method={method}, ref={reference})"
        )
        return p

    def mark_sent(self):
        if self.status in [self.Status.DRAFT, self.Status.OVERDUE]:
            self.status = self.Status.SENT
            self.sent_at = timezone.now()
            self.save(update_fields=["status", "sent_at", "updated_at"])
            InvoiceAuditLog.objects.create(invoice=self, action="status_change", details="Marked as sent")

    def mark_overdue_if_needed(self):
        if self.status != self.Status.PAID and self.due_date and self.due_date < timezone.now().date():
            self.status = self.Status.OVERDUE
            self.save(update_fields=["status", "updated_at"])
            InvoiceAuditLog.objects.create(invoice=self, action="status_change", details="Marked overdue")

    def _generate_invoice_number(self):
        year = timezone.now().year
        org_code = getattr(self.organization, "code", "ORG")[:10].upper()

        # Use count in a transaction-safe way (brief race still possible; fallback to uuid)
        for attempt in range(5):
            count = Invoice.objects.filter(organization=self.organization, created_at__year=year).count() + 1
            candidate = f"{org_code}-{year}-{count:04d}"
            if not Invoice.objects.filter(invoice_number=candidate).exists():
                return candidate
        return f"{org_code}-{year}-{uuid.uuid4().hex[:6].upper()}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_invoice_number()
        super().save(*args, **kwargs)


class RevenueCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="revenue_categories")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("organization", "name")
        ordering = ("name",)

    def __str__(self):
        return f"{self.organization.name}: {self.name}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="items", on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    revenue_category = models.ForeignKey(RevenueCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="items")

    def total_price(self):
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))

    def __str__(self):
        return f"Item {self.description} (Invoice={self.invoice.invoice_number})"


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="payments", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    method = models.CharField(max_length=64, blank=True, default="")
    reference = models.CharField(max_length=128, blank=True, default="")
    received_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"Payment {self.amount} for {self.invoice.invoice_number}"


class InvoiceAuditLog(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="audit_logs", on_delete=models.CASCADE)
    action = models.CharField(max_length=64)
    details = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} for {self.invoice.invoice_number} at {self.created_at}"


class OrgPartnerShare(models.Model):
    SHARE_TYPE_CHOICES = (("percentage", "Percentage"), ("fixed", "FixedAmount"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="partner_shares")
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="org_shares")
    share_type = models.CharField(max_length=20, choices=SHARE_TYPE_CHOICES, default="percentage")
    share_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    priority = models.PositiveSmallIntegerField(default=10, help_text="Lower = allocated first")

    class Meta:
        unique_together = ("organization", "partner")
        ordering = ["priority"]

    def __str__(self):
        return f"{self.organization.name} - {self.partner.user.username} ({self.share_type} {self.share_value})"


class InvoicePartnerShare(models.Model):
    SHARE_TYPE_CHOICES = (("percentage", "Percentage"), ("fixed", "FixedAmount"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="partner_shares")
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="invoice_shares")
    share_type = models.CharField(max_length=20, choices=SHARE_TYPE_CHOICES, default="percentage")
    share_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    priority = models.PositiveSmallIntegerField(default=10)

    class Meta:
        unique_together = ("invoice", "partner")
        ordering = ["priority"]

    def __str__(self):
        return f"Invoice {self.invoice.invoice_number} - {self.partner.user.username} ({self.share_type} {self.share_value})"


class PartnerAllocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="allocations")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["payment"]), models.Index(fields=["partner"])]

    def __str__(self):
        return f"{self.partner.user.username} <- {self.amount} (payment={self.payment.id})"
