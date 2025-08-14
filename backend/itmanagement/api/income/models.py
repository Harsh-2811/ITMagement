from django.db import models , transaction
from decimal import Decimal
from django.utils import timezone
from django.conf import settings

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ]
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField()
    client_country = models.CharField(max_length=100, default="India")
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    @transaction.atomic
    def record_payment(self, amount: Decimal):
        """
        Records payment and updates invoice status accordingly.
        """
        self.paid_amount += amount

        if self.paid_amount >= self.total_amount:
            self.status = "paid"
            self.paid_at = timezone.now()
        elif self.paid_amount > 0:
            self.status = "partially_paid"

        self.save(update_fields=["paid_amount", "status", "paid_at"]) 
    def calculate_tax_for_india(self):
        """Apply GST if country is India"""
        if self.client_country.lower() == "india":
            gst_rate = Decimal("18.00")  # 18%
            self.tax_amount = (self.subtotal_amount * gst_rate) / Decimal(100)
        else:
            self.tax_amount = Decimal("0.00")
        self.total_amount = self.subtotal_amount + self.tax_amount
        self.save()

    def mark_sent(self):
        self.status = "sent"
        self.save(update_fields=["status"])

    
    def mark_paid(self):
        """
         Marks the invoice as paid and records the payment date.
    """
        self.status = "paid"
        if hasattr(self, "paid_at"):
            self.paid_at = timezone.now()
            self.save(update_fields=["status", "paid_at"])
        else:
            self.save(update_fields=["status"])

    def check_overdue(self):
        if self.due_date < timezone.now().date() and self.status != "paid":
            self.status = "overdue"
            self.save(update_fields=["status"])


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="items", on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_price(self):
        return self.quantity * self.unit_price