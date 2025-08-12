from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import Organization
from .serializers import (
    OrganizationRegistrationSerializer, 
    OrganizationApprovalSerializer,
    OrganizationDetailSerializer
)
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from api.users.models import User


class OrganizationRegisterView(generics.CreateAPIView):
    serializer_class = OrganizationRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            organization = serializer.save()
            
            # Send notification to admin about new organization registration
            try:
                send_mail(
                    subject=f'New Organization Registration - {organization.name}',
                    message=f'A new organization "{organization.name}" has registered and is waiting for approval.',
                    from_email=organization.email,
                    recipient_list=['admin@example.com'],  # Replace with actual admin email
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send admin notification: {e}")
            
            return Response({
                'message': 'Organization registered successfully. Waiting for admin approval.',
                'organization_id': organization.id
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationApproveView(generics.UpdateAPIView):
    serializer_class = OrganizationApprovalSerializer
    queryset = Organization.objects.all()
    permission_classes = [permissions.IsAdminUser]

    def perform_update(self, serializer):
        organization = self.get_object()
        main_partner_user = organization.get_main_partner_user()
        
        if not main_partner_user:
            raise ValueError("No main partner found for this organization")

        # Generate temporary password
        temp_password = get_random_string(length=12)
        main_partner_user.password = make_password(temp_password)
        main_partner_user.is_verified = True
        main_partner_user.save()
        
        print(f"[TEMP PASSWORD] Org: {organization.name}, User: {main_partner_user.username}, Temp Password: {temp_password}")

        # Update organization status
        serializer.save(verification_status='approved', is_active=True)

        # Send approval email with temporary password
        try:
            send_mail(
                subject=f'Organization Approved - {organization.name}',
                message=f"""
Hi {main_partner_user.first_name},

Congratulations! Your organization '{organization.name}' has been approved.

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
        except Exception as e:
            print(f"Failed to send approval email: {e}")


class OrganizationListView(generics.ListAPIView):
    serializer_class = OrganizationDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        return Organization.objects.all().order_by('-created_at')


class PendingOrganizationListView(generics.ListAPIView):
    serializer_class = OrganizationDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        return Organization.objects.filter(verification_status='pending').order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def reject_organization(request, pk):
    try:
        organization = Organization.objects.get(pk=pk)
        organization.verification_status = 'rejected'
        organization.save()
        
        # Send rejection email
        main_partner_user = organization.get_main_partner_user()
        if main_partner_user:
            try:
                send_mail(
                    subject=f'Organization Registration Rejected - {organization.name}',
                    message=f"""
Hi {main_partner_user.first_name},

We regret to inform you that your organization registration for '{organization.name}' has been rejected.

If you have any questions, please contact our support team.

Best regards,
Admin Team
                    """,
                    from_email='admin@example.com',
                    recipient_list=[main_partner_user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send rejection email: {e}")
        
        return Response({'message': 'Organization rejected successfully'}, status=status.HTTP_200_OK)
    except Organization.DoesNotExist:
        return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)