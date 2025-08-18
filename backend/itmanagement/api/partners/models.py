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
    Partner-specific share configuration for a particular income/expense.
    Works alongside OrgPartnerShare to define how profits/revenue/expenses
    are distributed among organization partners.

    - share_type: 'percentage' or 'fixed'
    - If 'percentage', share_value is stored as a percentage (20.00 = 20%).
    - If 'fixed', share_value is stored as a currency amount (e.g., 500.00).
    """

    SHARE_TYPE_CHOICES = (
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    )

    id = models.BigAutoField(primary_key=True)
    partner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="partner_shares",
        help_text="The partner receiving this share.",
    )
    income = models.ForeignKey(
        "income.Income",
        on_delete=models.CASCADE,
        related_name="partner_shares",
        null=True,
        blank=True,
        help_text="The income record this share belongs to (optional).",
    )
    expense = models.ForeignKey(
        "expense.Expense",
        on_delete=models.CASCADE,
        related_name="partner_shares",
        null=True,
        blank=True,
        help_text="The expense record this share belongs to (optional).",
    )
    share_type = models.CharField(
        max_length=20,
        choices=SHARE_TYPE_CHOICES,
        default="percentage",
        help_text="Whether this share is a percentage or fixed amount.",
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
        help_text="Final calculated share amount in currency.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Partner Share"
        verbose_name_plural = "Partner Shares"
        unique_together = ("partner", "income", "expense")

    def __str__(self):
        target = self.income or self.expense
        return f"{self.partner} → {self.share_value} ({self.get_share_type_display()}) for {target}"

    def calculate_share(self, base_amount: Decimal) -> Decimal:
        """
        Calculate the share amount based on type and update calculated_amount.
        """
        if self.share_type == "percentage":
            self.calculated_amount = (base_amount * self.share_value) / Decimal("100.00")
        else:
            self.calculated_amount = self.share_value

        return self.calculated_amount
