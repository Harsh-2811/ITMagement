from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role', 'permissions', 'is_active', 'invited_by', 'invited_at')
