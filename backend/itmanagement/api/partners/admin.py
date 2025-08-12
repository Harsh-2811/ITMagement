from django.contrib import admin
from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = [
        'get_partner_name', 'get_partner_email', 'organization', 
        'role', 'permissions', 'is_active', 'invited_at'
    ]
    list_filter = ['role', 'permissions', 'is_active', 'organization']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['invited_at', 'accepted_at']
    
    def get_partner_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}" if obj.user else 'No User'
    get_partner_name.short_description = 'Partner Name'
    
    def get_partner_email(self, obj):
        return obj.user.email if obj.user else 'No Email'
    get_partner_email.short_description = 'Email'