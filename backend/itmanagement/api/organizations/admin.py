from django.contrib import admin
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .models import Organization
import logging

logger = logging.getLogger(__name__)

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'legal_name', 'get_main_partner_email', 
        'verification_status', 'is_active', 'created_at'
    ]
    list_filter = ['verification_status', 'is_active', 'created_at']
    search_fields = ['name', 'legal_name', 'registration_number']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_organizations', 'reject_organizations']

    def get_main_partner_email(self, obj):
        main_partner_user = obj.get_main_partner_user()
        return main_partner_user.email if main_partner_user else 'No main partner'
    get_main_partner_email.short_description = 'Main Partner Email'

    def save_model(self, request, obj, form, change):
        # Check if verification_status is being changed
        if change and 'verification_status' in form.cleaned_data:
            old_status = Organization.objects.get(pk=obj.pk).verification_status
            new_status = form.cleaned_data['verification_status']
            
            if old_status != 'approved' and new_status == 'approved':
                # Trigger approval email
                self.send_approval_email(obj)
                self.message_user(request, f"Approval email sent to {obj.get_main_partner_user().email if obj.get_main_partner_user() else 'N/A'}", level='SUCCESS')
            elif old_status != 'rejected' and new_status == 'rejected':
                # Trigger rejection email
                self.send_rejection_email(obj)
                self.message_user(request, f"Rejection email sent to {obj.get_main_partner_user().email if obj.get_main_partner_user() else 'N/A'}", level='INFO')
        
        super().save_model(request, obj, form, change)

    def send_approval_email(self, org):
        """Send approval email to main partner"""
        main_partner_user = org.get_main_partner_user()
        if not main_partner_user:
            logger.error(f"No main partner found for organization {org.name}")
            return

        try:
            # Generate temporary password
            temp_password = get_random_string(length=8)
            main_partner_user.password = make_password(temp_password)
            main_partner_user.is_verified = True
            main_partner_user.save()
            
            # Generate reset password style token and UUID
            verification_token = PasswordResetTokenGenerator().make_token(main_partner_user)
            uidb64 = urlsafe_base64_encode(force_bytes(main_partner_user.pk))
            reset_link = f"{settings.FRONTEND_URL}/reset-password/{uidb64}/{verification_token}/"
            
            # Store verification token temporarily
            cache.set(f'verify_org_{verification_token}', {
                'org_id': str(org.id),
                'temp_password': temp_password,
                'user_id': str(main_partner_user.id)
            }, timeout=604800)  # 1 week expiry (7 days * 24 hours * 3600 seconds)

            # Send approval email with reset password style link
            send_mail(
                subject=f'Organization Verification Required - {org.name}',
                message=f"""
Hi {main_partner_user.first_name},

Congratulations! Your organization '{org.name}' has been preliminarily approved.

Organization Details:
• Name: {org.name}
• Email: {org.company_email}
• Phone: {org.company_phone}
• Address: {org.address}, {org.city}, {org.state}
• Registration Number: {org.registration_number}

You can login with:
Username: {main_partner_user.username}
Temporary Password: {temp_password}

Click the link below to verify your organization and activate your account:
{reset_link}

⚠️ IMPORTANT: This link is valid for 1 week. You must verify within this timeframe.

Best regards,
Admin Team
                """,
                from_email='khokhariavidhya@gmail.com',
                recipient_list=[main_partner_user.email],
                fail_silently=False,
            )
            
            logger.info(f"Approval email sent successfully to {main_partner_user.email} for organization {org.name}")
            
        except Exception as e:
            logger.error(f"Failed to send approval email for organization {org.name}: {e}")
            raise

    def send_rejection_email(self, org):
        """Send rejection email to main partner"""
        main_partner_user = org.get_main_partner_user()
        if not main_partner_user:
            logger.error(f"No main partner found for organization {org.name}")
            return

        try:
            send_mail(
                subject=f'Organization Registration Rejected - {org.name}',
                message=f"""
Hi {main_partner_user.first_name},

We regret to inform you that your organization registration for '{org.name}' has been rejected.

Organization Details:
• Name: {org.name}
• Email: {org.company_email}
• Phone: {org.company_phone}
• Address: {org.address}, {org.city}, {org.state}
• Registration Number: {org.registration_number}

If you have any questions or would like to appeal this decision, please contact our support team.

We appreciate your interest in our platform and encourage you to review your application details for any issues that may have led to this rejection.

Best regards,
Admin Team
                """,
                from_email='khokhariavidhya@gmail.com',
                recipient_list=[main_partner_user.email],
                fail_silently=False,
            )
            
            logger.info(f"Rejection email sent successfully to {main_partner_user.email} for organization {org.name}")
            
        except Exception as e:
            logger.error(f"Failed to send rejection email for organization {org.name}: {e}")
            raise

    def approve_organizations(self, request, queryset):
        approved_count = 0
        for org in queryset:
            if org.verification_status != 'approved':
                main_partner_user = org.get_main_partner_user()
                if main_partner_user:
                    try:
                        temp_password = get_random_string(length=8)
                        main_partner_user.password = make_password(temp_password)
                        main_partner_user.is_verified = True
                        main_partner_user.save()
                        
                        # Generate reset password style token and UUID
                        verification_token = PasswordResetTokenGenerator().make_token(main_partner_user)
                        uidb64 = urlsafe_base64_encode(force_bytes(main_partner_user.pk))
                        reset_link = f"{settings.FRONTEND_URL}/reset-password/{uidb64}/{verification_token}/"
                        
                        # Store verification token temporarily
                        cache.set(f'verify_org_{verification_token}', {
                            'org_id': str(org.id),
                            'temp_password': temp_password,
                            'user_id': str(main_partner_user.id)
                        }, timeout=604800)  # 1 week expiry (7 days * 24 hours * 3600 seconds)
                        
                        self.message_user(request, f"Temp password for {org.name}: {temp_password}", level='SUCCESS')
     
                        org.verification_status = 'approved'
                        org.is_active = True
                        org.save()

                        # Send approval email
                        send_mail(
                            subject=f'Organization Verification Required - {org.name}',
                            message=f"""
Hi {main_partner_user.first_name},

Congratulations! Your organization '{org.name}' has been preliminarily approved.

Organization Details:
• Name: {org.name}
• Email: {org.company_email}
• Phone: {org.company_phone}
• Address: {org.address}, {org.city}, {org.state}
• Registration Number: {org.registration_number}

You can login with:
Username: {main_partner_user.username}
Temporary Password: {temp_password}

Click the link below to verify your organization and activate your account:
{reset_link}

⚠️ IMPORTANT: This link is valid for 1 week. You must verify within this timeframe.

Best regards,
Admin Team
                            """,
                            from_email='khokhariavidhya@gmail.com',
                            recipient_list=[main_partner_user.email],
                            fail_silently=False,
                        )
                        approved_count += 1
                    except Exception as e:
                        self.message_user(request, f"Failed to send email for {org.name}: {e}", level='ERROR')
        
        self.message_user(request, f"Successfully approved {approved_count} organizations.")
    approve_organizations.short_description = "Approve selected organizations"

    def reject_organizations(self, request, queryset):
        rejected_count = 0
        for org in queryset:
            if org.verification_status == 'pending':
                org.verification_status = 'rejected'
                org.save()
                
                main_partner_user = org.get_main_partner_user()

                if main_partner_user:
                    try:
                        send_mail(
                            subject=f'Organization Registration Rejected - {org.name}',
                            message=f"""
Hi {main_partner_user.first_name},

We regret to inform you that your organization registration for '{org.name}' has been rejected.

If you have any questions, please contact our support team.

Best regards,
Admin Team
                            """,
                            from_email='khokhariavidhya@gmail.com',
                            recipient_list=[main_partner_user.email],
                            fail_silently=False,
                        )
                        rejected_count += 1
                    except Exception as e:
                        self.message_user(request, f"Failed to send rejection email for {org.name}: {e}", level='ERROR')
        
        self.message_user(request, f"Successfully rejected {rejected_count} organizations.")
    reject_organizations.short_description = "Reject selected organizations"