from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from api.users.models import User
from .models import Organization
from drf_spectacular.utils import extend_schema_field

class MainPartnerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'first_name', 'last_name', 'password']

    def create(self, validated_data):
        validated_data['user_type'] = 'organization_admin'
        validated_data['is_verified'] = False
        validated_data['password'] = make_password(validated_data['password'])
        return User.objects.create(**validated_data)


class OrganizationRegistrationSerializer(serializers.ModelSerializer):
    main_partner = MainPartnerSerializer()

    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = ['verification_status', 'is_active']

    def create(self, validated_data):
        print(f"[DEBUG] OrganizationRegistrationSerializer.create called")
        print(f"[DEBUG] validated_data keys: {list(validated_data.keys())}")
        
        partner_data = validated_data.pop('main_partner')
        print(f"[DEBUG] partner_data: {partner_data}")
        
        # Create the user first
        partner_user = MainPartnerSerializer().create(partner_data)
        print(f"[DEBUG] Created partner user: {partner_user.id} - {partner_user.username}")
        
        # Create organization
        org = Organization.objects.create(**validated_data)
        print(f"[DEBUG] Created organization: {org.id} - {org.name}")
        
        # Create partner profile linking user to organization
        from api.partners.models import Partner
        partner = Partner.objects.create(
            user=partner_user,
            organization=org,
            role='main_partner',
            permissions='all'
        )
        print(f"[DEBUG] Created partner profile: {partner.id}")
        
        return org


class OrganizationApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'verification_status', 'is_active']
        read_only_fields = ['id', 'name']


class OrganizationDetailSerializer(serializers.ModelSerializer):
    main_partner_email = serializers.SerializerMethodField()
    main_partner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = '__all__'
    
    def get_main_partner_email(self, obj):
        main_partner_user = obj.get_main_partner_user()
        return main_partner_user.email if main_partner_user else None
    @extend_schema_field(str)
    def get_main_partner_name(self, obj):
        main_partner_user = obj.get_main_partner_user()
        return f"{main_partner_user.first_name} {main_partner_user.last_name}" if main_partner_user else None