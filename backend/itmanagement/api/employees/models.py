from django.db import models
import uuid
from api.users.models import User
from api.organizations.models import Organization

class Employee(models.Model):
    ROLE_CHOICES = [
        ('developer', 'Developer'),
        ('manager', 'Manager'),
        ('qa', 'QA'),
        ('intern', 'Intern'),
    ]

    PERMISSION_CHOICES = [
        ('all', 'All Permissions'),
        ('limited', 'Limited Permissions'),
        ('view_only', 'View Only'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='employees')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    permissions = models.CharField(max_length=30, choices=PERMISSION_CHOICES)
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='invited_employees')
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role} @ {self.organization.name}"
