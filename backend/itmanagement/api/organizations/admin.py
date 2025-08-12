from django.contrib import admin
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
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

    def approve_organizations(self, request, queryset):
        approved_count = 0
        for org in queryset:
            if org.verification_status != 'approved':
                main_partner_user = org.get_main_partner_user()
                if main_partner_user:
                    # Generate temporary password
                    temp_password = get_random_string(length=12)
                    main_partner_user.password = make_password(temp_password)
                    main_partner_user.is_verified = True
                    main_partner_user.save()
                    
                    # Log to console (this will appear in your terminal)
                    # logger.info(f"[TEMP PASSWORD] Org: {org.name}, User: {main_partner_user.username}, Password: {temp_password}")
                    print(f"[TEMP PASSWORD] Org: {org.name}, User: {main_partner_user.username}, Password: {temp_password}")

                    self.message_user(request, f"Temp password for {org.name}: {temp_password}", level='SUCCESS')
 
                    org.verification_status = 'approved'
                    org.is_active = True
                    org.save()

                    # Send approval email
                    try:
                        send_mail(
                            subject=f'Organization Approved - {org.name}',
                            message=f"""
Hi {main_partner_user.first_name},

Congratulations! Your organization '{org.name}' has been approved.

You can now login with the following credentials:
Username: {main_partner_user.username}
Temporary Password: {temp_password}

Please login and change your password immediately for security purposes.

Best regards,
Admin Team
                            """,
                            from_email='admin@example.com',
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
                print(" sorry for rejection")

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
                            from_email='admin@example.com',
                            recipient_list=[main_partner_user.email],
                            fail_silently=False,
                        )
                        rejected_count += 1
                    except Exception as e:
                        self.message_user(request, f"Failed to send rejection email for {org.name}: {e}", level='ERROR')
        
        self.message_user(request, f"Successfully rejected {rejected_count} organizations.")
    reject_organizations.short_description = "Reject selected organizations"