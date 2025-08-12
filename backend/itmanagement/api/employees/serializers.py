from rest_framework import serializers
from api.users.models import User
from .models import Employee

class EmployeeInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(required=False)
    role = serializers.ChoiceField(choices=Employee.ROLE_CHOICES)
    permissions = serializers.ChoiceField(choices=Employee.PERMISSION_CHOICES)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

class EmployeeDetailSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    invited_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = '__all__'

    def get_user(self, obj):
        return {
            "email": obj.user.email,
            "username": obj.user.username,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
            "phone": obj.user.phone,
            "is_verified": obj.user.is_verified,
        }

    def get_invited_by_name(self, obj):
        return f"{obj.invited_by.first_name} {obj.invited_by.last_name}" if obj.invited_by else None
