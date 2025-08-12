from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from django.core.mail import send_mail

from api.users.models import User
from api.organizations.models import Organization
from api.partners.models import Partner
from .models import Employee
from .serializers import EmployeeInviteSerializer, EmployeeDetailSerializer

class IsMainPartnerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return Partner.objects.filter(user=request.user, role='main_partner').exists()

class EmployeeInviteView(generics.CreateAPIView):
    serializer_class = EmployeeInviteSerializer
    permission_classes = [permissions.IsAuthenticated, IsMainPartnerOrAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Get the organization
            partner = Partner.objects.filter(user=request.user, role='main_partner').first()
            if not partner:
                return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
            organization = partner.organization
            temp_password = get_random_string(length=12)

            user = User.objects.create(
                username=serializer.validated_data['email'],
                email=serializer.validated_data['email'],
                first_name=serializer.validated_data['first_name'],
                last_name=serializer.validated_data['last_name'],
                phone=serializer.validated_data.get('phone', ''),
                user_type='employee',
                password=make_password(temp_password),
                is_verified=False
            )

            employee = Employee.objects.create(
                user=user,
                organization=organization,
                role=serializer.validated_data['role'],
                permissions=serializer.validated_data['permissions'],
                invited_by=request.user
            )

            try:
                send_mail(
                    subject=f'You are invited to join {organization.name}',
                    message=f"""
Hi {user.first_name},

You have been invited to join {organization.name} as a {employee.role}.

Login credentials:
Username: {user.username}
Temporary Password: {temp_password}

Please login and change your password after first login.

Thanks,
{request.user.first_name}
                    """,
                    from_email='admin@example.com',
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send email: {e}")

            return Response({
                'message': 'Employee invited successfully',
                'employee_id': employee.id,
                'email': user.email,
                'temp_password': temp_password  # You can remove this in production
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
