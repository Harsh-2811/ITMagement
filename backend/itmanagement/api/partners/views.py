from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from api.users.models import User
from api.organizations.models import Organization
from .models import Partner
from .serializers import (
    PartnerSerializer,
    PartnerInvitationSerializer,
    PartnerDetailSerializer
)


class IsMainPartnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow main partners or admin users to invite other partners.
    """
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        
        if request.user.user_type == 'organization_admin':
            # Check if user is main partner
            partner = Partner.objects.filter(user=request.user, role='main_partner').first()
            return partner is not None
        
        return False


class PartnerInviteView(generics.CreateAPIView):
    serializer_class = PartnerInvitationSerializer
    permission_classes = [permissions.IsAuthenticated, IsMainPartnerOrAdmin]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Get the organization of the current user (main partner)
            current_partner = Partner.objects.filter(user=request.user, role='main_partner').first()
            if not current_partner:
                return Response({'error': 'You are not authorized to invite partners'}, 
                              status=status.HTTP_403_FORBIDDEN)
            
            organization = current_partner.organization
            
            # Generate temporary password
            temp_password = get_random_string(length=12)
            print(f"[INVITE] New partner invited to '{organization.name}'")

            print(f"[TEMP PASSWORD] Username: {serializer.validated_data['email']}, Password: {temp_password}")
            
            # Create new user
            user_data = {
                'username': serializer.validated_data['email'],
                'email': serializer.validated_data['email'],
                'first_name': serializer.validated_data['first_name'],
                'last_name': serializer.validated_data['last_name'],
                'phone': serializer.validated_data.get('phone', ''),
                'user_type': 'partner',
                'password': make_password(temp_password),
                'is_verified': False
            }
            
            new_user = User.objects.create(**user_data)
            
            # Create partner profile
            partner = Partner.objects.create(
                user=new_user,
                organization=organization,
                role=serializer.validated_data['role'],
                permissions=serializer.validated_data['permissions'],
                invited_by=request.user
            )
            
            # Send invitation email
            try:
                send_mail(
                    subject=f'Partnership Invitation - {organization.name}',
                    message=f"""
Hi {new_user.first_name},

You have been invited to join {organization.name} as a {partner.role}.

Login credentials:
Username: {new_user.username}
Temporary Password: {temp_password}

Please login and change your password immediately.

Best regards,
{request.user.first_name} {request.user.last_name}
                    """,
                    from_email='admin@example.com',
                    recipient_list=[new_user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send invitation email: {e}")
            
            return Response({
                'message': 'Partner invited successfully',
                'partner_id': partner.id,
                'partner_email': new_user.email
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PartnerListView(generics.ListAPIView):
    serializer_class = PartnerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            return Partner.objects.all()
        
        if user.user_type in ['organization_admin', 'partner']:
            # Get partners from the same organization
            user_partner = Partner.objects.filter(user=user).first()
            if user_partner:
                return Partner.objects.filter(organization=user_partner.organization)
        
        return Partner.objects.none()


class PartnerDetailView(generics.RetrieveAPIView):
    serializer_class = PartnerDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            return Partner.objects.all()
        
        if user.user_type in ['organization_admin', 'partner']:
            user_partner = Partner.objects.filter(user=user).first()
            if user_partner:
                return Partner.objects.filter(organization=user_partner.organization)
        
        return Partner.objects.none()


class PartnerUpdateView(generics.UpdateAPIView):
    serializer_class = PartnerSerializer
    permission_classes = [permissions.IsAuthenticated, IsMainPartnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            return Partner.objects.all()
        
        if user.user_type == 'organization_admin':
            user_partner = Partner.objects.filter(user=user, role='main_partner').first()
            if user_partner:
                return Partner.objects.filter(organization=user_partner.organization)
        
        return Partner.objects.none()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsMainPartnerOrAdmin])
def deactivate_partner(request, pk):
    try:
        # Get the partner to deactivate
        partner = Partner.objects.get(pk=pk)
        
        # Check if current user has permission to deactivate this partner
        current_partner = Partner.objects.filter(user=request.user, role='main_partner').first()
        if not current_partner or partner.organization != current_partner.organization:
            return Response({'error': 'You are not authorized to deactivate this partner'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Cannot deactivate main partner
        if partner.role == 'main_partner':
            return Response({'error': 'Cannot deactivate main partner'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        partner.is_active = False
        partner.save()
        
        return Response({'message': 'Partner deactivated successfully'}, status=status.HTTP_200_OK)
    except Partner.DoesNotExist:
        return Response({'error': 'Partner not found'}, status=status.HTTP_404_NOT_FOUND)