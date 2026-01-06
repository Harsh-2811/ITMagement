from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import uuid
from api.users.models import User


class Organization(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True)
    tax_id = models.CharField(max_length=100, blank=True)

    company_email = models.EmailField()
    company_phone = models.CharField(max_length=20)
    website = models.URLField(blank=True)

    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    business_license = models.FileField(upload_to='org/docs/',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'png'])])
    tax_certificate = models.FileField(upload_to='org/docs/',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'png'])], blank=True)

    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def main_partner(self):
        """Get the main partner of this organization"""
        from api.partners.models import Partner
        return Partner.objects.filter(organization=self, role='main_partner').first()

    def get_main_partner_user(self):
        """Get the main partner user"""
        main_partner = self.main_partner
        return main_partner.user if main_partner else None