from rest_framework import serializers
from api.users.models import User
from .models import Partner


class PartnerUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'is_verified']
        read_only_fields = ['id', 'is_verified']


class PartnerSerializer(serializers.ModelSerializer):
    user = PartnerUserSerializer(read_only=True)
    invited_by_name = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = '__all__'
        read_only_fields = ['id', 'invited_by', 'invited_at', 'accepted_at']

    def get_invited_by_name(self, obj):
        if obj.invited_by:
            return f"{obj.invited_by.first_name} {obj.invited_by.last_name}"
        return None

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None


class PartnerInvitationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    phone = serializers.CharField(max_length=20, required=False)
    role = serializers.ChoiceField(choices=Partner.ROLE_CHOICES, default='partner')
    permissions = serializers.ChoiceField(choices=Partner.PERMISSION_CHOICES, default='limited')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class PartnerDetailSerializer(serializers.ModelSerializer):
    user = PartnerUserSerializer(read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    invited_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = '__all__'

    def get_invited_by_name(self, obj):
        if obj.invited_by:
            return f"{obj.invited_by.first_name} {obj.invited_by.last_name}"
        return None