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