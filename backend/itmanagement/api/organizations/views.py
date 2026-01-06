from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.openapi import OpenApiParameter
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
import json


class MixedFormatParser(MultiPartParser):
    """
    Custom parser that handles mixed format:
    - main_partner as JSON object
    - other fields as form data
    """
    
    def parse(self, stream, media_type=None, parser_context=None):
        # Parse the multipart form data
        parser = MultiPartParser()
        result = parser.parse(stream, media_type, parser_context)
        
        # Debug print all received data
        print(f"[DEBUG PARSER] Raw result.data keys: {list(result.data.keys())}")
        print(f"[DEBUG PARSER] Raw result.files keys: {list(result.files.keys()) if hasattr(result, 'files') else 'No files attr'}")
        print(f"[DEBUG PARSER] business_license: {result.data.get('business_license')}")
        print(f"[DEBUG PARSER] tax_certificate: {result.data.get('tax_certificate')}")
        print(f"[DEBUG PARSER] business_license type: {type(result.data.get('business_license'))}")
        print(f"[DEBUG PARSER] tax_certificate type: {type(result.data.get('tax_certificate'))}")
        print(f"[DEBUG PARSER] main_partner: {result.data.get('main_partner')}")
        
        # CREATE NEW MUTABLE DICT instead of modifying QueryDict
        new_data = {}
        
        # Copy all form data to new dict
        for key, value in result.data.items():
            if hasattr(value, 'list'):
                # Handle QueryDict values that might be lists
                new_data[key] = value.list() if len(value.list()) > 1 else value.list()[0]
            else:
                new_data[key] = value
        
        # RESTORE FILES from result.files to new_data
        if hasattr(result, 'files') and result.files:
            print(f"[DEBUG PARSER] Restoring files: {list(result.files.keys())}")
            for file_key, file_value in result.files.items():
                print(f"[DEBUG PARSER] File {file_key} type: {type(file_value)}")
                print(f"[DEBUG PARSER] File {file_key} value: {file_value}")
                print(f"[DEBUG PARSER] File {file_key} repr: {repr(file_value)}")
                new_data[file_key] = file_value
                print(f"[DEBUG PARSER] Restored {file_key}: {file_value}")
        
        # Handle main_partner as JSON
        main_partner_value = new_data.get('main_partner')
        if isinstance(main_partner_value, str):
            try:
                parsed_json = json.loads(main_partner_value)
                print(f"[DEBUG PARSER] Parsed main_partner JSON: {parsed_json}")
                new_data['main_partner'] = parsed_json
                print(f"[DEBUG PARSER] Updated new_data with parsed main_partner")
            except json.JSONDecodeError:
                print(f"[DEBUG PARSER] JSON decode error for main_partner")
                pass  # Keep original if parsing fails
        elif isinstance(main_partner_value, (dict, list)):
            print(f"[DEBUG PARSER] main_partner is already structured data")
            pass  # Already in correct format
        
        # Replace result.data with our new mutable dict
        result.data = new_data
        
@extend_schema(
    summary="Register Organization",
    description="Register a new organization with main partner. Accepts mixed format: main_partner as JSON object + other fields as form data.",
    request={
        'multipart/form-data': OrganizationRegistrationSerializer,
    },
    responses={201: OrganizationRegistrationSerializer}
)
class OrganizationRegisterView(generics.CreateAPIView):
    serializer_class = OrganizationRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_first_error_message(self, errors):
        """
        Extract the first error message from the errors dict for frontend-friendly display.
        Returns a simple string message instead of nested arrays.
        """
        if not errors:
            return "Validation failed"
        
        # Get the first field with errors
        first_field = next(iter(errors))
        field_errors = errors[first_field]
        
        # Handle different error formats
        if isinstance(field_errors, list):
            # Return the first error message from the array
            return str(field_errors[0]) if field_errors else f"{first_field} is invalid"
        elif isinstance(field_errors, dict):
            # Handle nested errors (like main_partner)
            nested_field = next(iter(field_errors))
            nested_errors = field_errors[nested_field]
            if isinstance(nested_errors, list) and nested_errors:
                return f"{first_field}.{nested_field}: {str(nested_errors[0])}"
            else:
                return f"{first_field}.{nested_field} is invalid"
        else:
            # Handle string errors
            return str(field_errors)

    def create(self, request, *args, **kwargs):
        try:
            # Debug print what we received
            print(f"[DEBUG VIEW] request.data keys: {list(request.data.keys())}")
            print(f"[DEBUG VIEW] request.FILES keys: {list(request.FILES.keys())}")
            print(f"[DEBUG VIEW] business_license in data: {request.data.get('business_license')}")
            print(f"[DEBUG VIEW] business_license in FILES: {request.FILES.get('business_license')}")
            print(f"[DEBUG VIEW] tax_certificate in data: {request.data.get('tax_certificate')}")
            print(f"[DEBUG VIEW] tax_certificate in FILES: {request.FILES.get('tax_certificate')}")
            print(f"[DEBUG VIEW] main_partner raw: {request.data.get('main_partner')}")
            
            # Handle main_partner JSON parsing if it's a string
            main_partner_value = request.data.get('main_partner')
            website_value = request.data.get('website', '')
            
            # Create a clean data dict for the serializer (exclude files completely)
            data_for_serializer = {}
            
            # Copy only non-file fields
            for key, value in request.data.items():
                if key not in ['business_license', 'tax_certificate']:
                    # Ensure we're not copying any file-like objects
                    if not hasattr(value, 'read') and not hasattr(value, 'seek'):
                        data_for_serializer[key] = value
                    else:
                        print(f"[DEBUG VIEW] Skipped file-like object for key: {key}")
            
            # Add files back to data_for_serializer so serializer can see them
            if 'business_license' in request.FILES:
                data_for_serializer['business_license'] = request.FILES['business_license']
                print(f"[DEBUG VIEW] Added business_license from FILES")
            if 'tax_certificate' in request.FILES:
                data_for_serializer['tax_certificate'] = request.FILES['tax_certificate']
                print(f"[DEBUG VIEW] Added tax_certificate from FILES")
            
            # Handle main_partner JSON parsing
            if main_partner_value and isinstance(main_partner_value, str):
                try:
                    main_partner_data = json.loads(main_partner_value)
                    data_for_serializer['main_partner'] = main_partner_data
                    print(f"[DEBUG VIEW] Parsed main_partner: {main_partner_data}")
                except json.JSONDecodeError as e:
                    print(f"[DEBUG VIEW] Failed to parse main_partner JSON: {e}")
                    data_for_serializer['main_partner'] = main_partner_value
            
            # Handle website field - URLField(blank=True) allows empty string
            if not website_value or website_value.strip() == '':
                data_for_serializer['website'] = ''  # Empty string is valid for blank=True
                print(f"[DEBUG VIEW] Set website to empty string")
            else:
                # Ensure it's a valid URL format
                if not website_value.startswith(('http://', 'https://')):
                    website_value = 'https://' + website_value
                data_for_serializer['website'] = website_value
                print(f"[DEBUG VIEW] Set website to: {website_value}")
            
            print(f"[DEBUG VIEW] Final data_for_serializer keys: {list(data_for_serializer.keys())}")
            print(f"[DEBUG VIEW] Final main_partner: {data_for_serializer.get('main_partner')}")
            print(f"[DEBUG VIEW] Has business_license file: {'business_license' in data_for_serializer}")
            print(f"[DEBUG VIEW] Has tax_certificate file: {'tax_certificate' in data_for_serializer}")
            
            # Create serializer with clean data (files included from request.FILES)
            serializer = self.get_serializer(data=data_for_serializer)
            if serializer.is_valid():
                organization = serializer.save()
                
                # Send notification to admin about new organization registration
                try:
                    send_mail(
                        subject=f'New Organization Registration - {organization.name}',
                        message=f'A new organization "{organization.name}" has registered and is waiting for approval.',
                        from_email=organization.company_email,
                        recipient_list=['khokhariavidhya@gmail.com'],  # Admin email for notifications
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.error(f"Failed to send admin notification: {e}")
                
                return Response({
                    'message': 'Organization registered successfully. Waiting for admin approval.',
                    'organization_id': organization.id,
                    'submitted_data': {
                        'organization_fields': {
                            'name': request.data.get('name'),
                            'legal_name': request.data.get('legal_name'),
                            'company_email': request.data.get('company_email'),
                            'company_phone': request.data.get('company_phone'),
                            'website': request.data.get('website'),
                            'address': request.data.get('address'),
                            'city': request.data.get('city'),
                            'state': request.data.get('state'),
                            'postal_code': request.data.get('postal_code'),
                            'country': request.data.get('country'),
                            'registration_number': request.data.get('registration_number'),
                            'tax_id': request.data.get('tax_id'),
                            'business_license': 'File uploaded' if request.FILES.get('business_license') else None,
                            'tax_certificate': 'File uploaded' if request.FILES.get('tax_certificate') else None
                        },
                        'main_partner': data_for_serializer.get('main_partner'),
                        'files_received': {
                            'business_license': bool(request.FILES.get('business_license')),
                            'tax_certificate': bool(request.FILES.get('tax_certificate'))
                        }
                    }
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'error': 'Validation failed',
                'message': self.get_first_error_message(serializer.errors),
                'errors': serializer.errors,
                'submitted_data': {
                    'organization_fields': {
                        'name': request.data.get('name'),
                        'company_email': request.data.get('company_email'),
                        'company_phone': request.data.get('company_phone'),
                        'address': request.data.get('address'),
                        'city': request.data.get('city'),
                        'state': request.data.get('state'),
                        'postal_code': request.data.get('postal_code'),
                        'country': request.data.get('country'),
                        'registration_number': request.data.get('registration_number'),
                        'business_license': 'File uploaded' if request.FILES.get('business_license') else None,
                        'tax_certificate': 'File uploaded' if request.FILES.get('tax_certificate') else None
                    },
                    'main_partner': data_for_serializer.get('main_partner'),
                    'files_received': {
                        'business_license': bool(request.FILES.get('business_license')),
                        'tax_certificate': bool(request.FILES.get('tax_certificate'))
                    }
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            print(f"[ERROR] Organization registration failed: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Registration failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        temp_password = get_random_string(length=8)
        main_partner_user.password = make_password(temp_password)
        main_partner_user.is_verified = True
        main_partner_user.save()
        
        print(f"[TEMP PASSWORD] Org: {organization.name}, User: {main_partner_user.username}, Temp Password: {temp_password}")

        # Update organization status
        serializer.save(verification_status='approved', is_active=True)

        # Generate reset password style token and UUID
        verification_token = PasswordResetTokenGenerator().make_token(main_partner_user)
        uidb64 = urlsafe_base64_encode(force_bytes(main_partner_user.pk))
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{uidb64}/{verification_token}/"
        
        print(f"[DEBUG] Generating reset password style verification for org: {organization.name}")
        print(f"[DEBUG] Main partner: {main_partner_user.email}")
        print(f"[DEBUG] Reset link: {reset_link}")
        
        # Store verification data with 1 week expiry
        from django.core.cache import cache
        cache.set(f'verify_org_{verification_token}', {
            'org_id': str(organization.id),
            'temp_password': temp_password,
            'user_id': str(main_partner_user.id)
        }, timeout=604800)  # 1 week expiry (7 days * 24 hours * 3600 seconds)
        
        try:
            print(f"[DEBUG] Sending approval email to: {main_partner_user.email}")
            print(f"[DEBUG] Email settings - Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}, User: {settings.EMAIL_HOST_USER}")
            print(f"[DEBUG] From email: {organization.company_email}")
            print(f"[DEBUG] To email: {main_partner_user.email}")
            
            result = send_mail(
                subject=f'Organization Verification Required - {organization.name}',
                message=f"""
Hi {main_partner_user.first_name},

Congratulations! Your organization '{organization.name}' has been preliminarily approved.

Organization Details:
• Name: {organization.name}
• Email: {organization.company_email}
• Phone: {organization.company_phone}
• Address: {organization.address}, {organization.city}, {organization.state}
• Registration Number: {organization.registration_number}

You can login with:
Username: {main_partner_user.username}
Temporary Password: {temp_password}

Click the link below to verify your organization and activate your account:
{reset_link}

⚠️ IMPORTANT: This link is valid for 1 week. You must verify within this timeframe.

Best regards,
Admin Team
                """,
                from_email=organization.company_email,
                recipient_list=[main_partner_user.email],
                fail_silently=False,
            )
            
            print(f"[DEBUG] Email send result: {result}")
            print(f"[DEBUG] Email result type: {type(result)}")
            print(f"[DEBUG] Email result value: {result}")
            print(f"[DEBUG] Email result dir: {dir(result)}")
            
            if result:
                print(f"[SUCCESS] Approval email sent successfully to {main_partner_user.email}")
                # Also try to send a copy to admin for backup
                try:
                    admin_result = send_mail(
                        subject=f'[COPY] Organization Verification Sent - {organization.name}',
                        message=f"""
Admin Copy: Organization verification email has been sent to {main_partner_user.email} for organization {organization.name}.

Verification Link: {verification_link}
Temp Password: {temp_password}

This is an automated backup notification.
                        """,
                        from_email='khokhariavidhya@gmail.com',
                        recipient_list=['khokhariavidhya@gmail.com'],
                        fail_silently=False,
                    )
                    print(f"[DEBUG] Admin backup notification sent: {admin_result}")
                except Exception as backup_e:
                    print(f"[ERROR] Failed to send admin backup notification: {backup_e}")
            else:
                print(f"[ERROR] Failed to send approval email to {main_partner_user.email}")
                print(f"[ERROR] Email error details: {result}")
                # Check if it's a specific email error
                if hasattr(result, 'recipients'):
                    print(f"[ERROR] Recipients: {result.recipients}")
                if hasattr(result, 'reason'):
                    print(f"[ERROR] Failure reason: {result.reason}")
        except Exception as e:
            print(f"[ERROR] Exception in approval email: {e}")
            print(f"[ERROR] Exception type: {type(e)}")
            print(f"[ERROR] Exception args: {e.args}")
            import traceback
            traceback.print_exc()


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
@permission_classes([permissions.AllowAny])
def verify_organization(request):
    """
    Verify organization from email link and activate it
    """
    try:
        token = request.data.get('token')
        org_id = request.data.get('org_id')
        
        if not token or not org_id:
            return Response({'error': 'Token and organization ID required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Get cached verification data
        from django.core.cache import cache
        cached_data = cache.get(f'verify_org_{token}')
        
        if not cached_data:
            return Response({'error': 'Invalid or expired verification token'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Verify organization
        organization = Organization.objects.get(id=cached_data['org_id'])
        main_partner_user = organization.get_main_partner_user()
        
        if not main_partner_user:
            return Response({'error': 'Main partner not found'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Activate organization and user
        organization.verification_status = 'approved'
        organization.is_active = True
        organization.save()
        
        main_partner_user.is_verified = True
        main_partner_user.save()
        
        # Clear cache
        cache.delete(f'verify_org_{token}')
        
        print(f"[VERIFICATION] Organization {organization.name} verified and activated")
        
        # Send confirmation email with login credentials
        try:
            send_mail(
                subject=f'Organization Verified Successfully - {organization.name}',
                message=f"""
Hi {main_partner_user.first_name},

🎉 Congratulations! Your organization '{organization.name}' has been successfully verified and activated.

Your organization is now LIVE and ready to use!

Login Credentials:
Username: {main_partner_user.username}
Temporary Password: {cached_data['temp_password']}

Please login immediately and change your password for security purposes.

Organization Dashboard: {settings.FRONTEND_URL}/dashboard
Support: If you need any help, contact our support team.

Best regards,
Admin Team
                """,
                from_email='khokhariavidhya@gmail.com',
                recipient_list=[main_partner_user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send verification confirmation email: {e}")
        
        return Response({
            'message': 'Organization verified and activated successfully',
            'organization_name': organization.name,
            'username': main_partner_user.username,
            'temp_password': cached_data['temp_password']
        }, status=status.HTTP_200_OK)
        
    except Organization.DoesNotExist:
        return Response({'error': 'Organization not found'}, 
                      status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"[ERROR] Organization verification failed: {e}")
        return Response({'error': 'Verification failed', 'details': str(e)}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def reject_organization(request, pk):
    try:
        organization = Organization.objects.get(pk=pk)
        organization.verification_status = 'rejected'
        organization.save()
        
        # Send rejection email to main partner
        main_partner_user = organization.get_main_partner_user()
        if main_partner_user:
            try:
                send_mail(
                    subject=f'Organization Registration Rejected - {organization.name}',
                    message=f"""
Hi {main_partner_user.first_name},

We regret to inform you that your organization registration for '{organization.name}' has been rejected.

Organization Details:
• Name: {organization.name}
• Email: {organization.company_email}
• Phone: {organization.company_phone}
• Address: {organization.address}, {organization.city}, {organization.state}
• Registration Number: {organization.registration_number}

If you have any questions or would like to appeal this decision, please contact our support team.

We appreciate your interest in our platform and encourage you to review your application details for any issues that may have led to this rejection.

Best regards,
Admin Team
                    """,
                    from_email='khokhariavidhya@gmail.com',
                    recipient_list=[main_partner_user.email],
                    fail_silently=False,
                )
                print(f"[SUCCESS] Rejection email sent to {main_partner_user.email} for organization {organization.name}")
            except Exception as e:
                print(f"[ERROR] Failed to send rejection email: {e}")
        
        return Response({'message': 'Organization rejected successfully'}, status=status.HTTP_200_OK)
    except Organization.DoesNotExist:
        return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)