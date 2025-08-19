from django.db import models
import uuid
from api.users.models import User
from api.organizations.models import Organization


class Partner(models.Model):
    ROLE_CHOICES = [
        ('main_partner', 'Main Partner'),
        ('partner', 'Partner'),
        ('viewer', 'Viewer'),
    ]

    PERMISSION_CHOICES = [
        ('all', 'All Permissions'),
        ('limited', 'Limited Permissions'),
        ('view_only', 'View Only'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='partner_profile')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='partners')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='partner')
    permissions = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='limited')
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_partners')
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'organization']

    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.role})"
    

from django.db import models
from django.conf import settings
from decimal import Decimal

class PartnerShare(models.Model):
    """
    Partner-specific share for invoices/payments.
    Works alongside OrgPartnerShare and InvoicePartnerShare.
    """

    SHARE_TYPE_CHOICES = (
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # partner = models.ForeignKey(
    #     "partners.Partner",   # use Partner model, not raw AUTH_USER
    #     on_delete=models.CASCADE,
    #     related_name="shares",
    #     help_text="The partner receiving this share.",
    # )
    # invoice = models.ForeignKey(
    #     "invoices.Invoice",
    #     on_delete=models.CASCADE,
    #     related_name="partner_shares_legacy",
    #     null=True,
    #     blank=True,
    #     help_text="The invoice this share belongs to.",
    # )
    share_type = models.CharField(
        max_length=20,
        choices=SHARE_TYPE_CHOICES,
        default="percentage",
    )
    share_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Percentage (e.g., 20.00) or fixed amount (e.g., 500.00).",
    )
    calculated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # class Meta:
    #     unique_together = ("partner", "invoice")

    def __str__(self):
        return f"{self.partner} → {self.share_value} ({self.get_share_type_display()}) for {self.invoice}"

    def calculate_share(self, base_amount: Decimal) -> Decimal:
        """Calculate share amount from invoice total."""
        if self.share_type == "percentage":
            self.calculated_amount = (base_amount * self.share_value) / Decimal("100.00")
        else:
            self.calculated_amount = self.share_value
        return self.calculated_amount
