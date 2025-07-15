import logging
from django.contrib.auth import get_user_model, login as django_login
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, status, viewsets ,permissions
from rest_framework.permissions import AllowAny, IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError as DRFValidationError, AuthenticationFailed
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from dynamic_form.models import FormSubmission

from .tokens import password_reset_token
from .permissions import IsSuperuserOrAdminRole
from .serializers import (
    ApplicantRegistrationSerializer, LoginSerializer, ProfileSerializer,
    RoleSerializer, AssignRoleSerializer, AssignPermissionSerializer,
    SubAuthUserSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, UserSerializer,
    ChangeUserRoleSerializer, AdminBulkUserCreateSerializer,
    EvaluatorUserSerializer,ProfileGetSerializer,
    InitialSignupSerializer,ProfileUpdateSerializer,ChangePasswordSerializer,AdminChangeUserPasswordSerializer
)
from .models import Role, SubAuthUser, Profile, UserRole
from configuration.models import CommitteeMember, ScreeningCommittee
from audit.drf import AuditMixin

logger = logging.getLogger(__name__)
User = get_user_model()


# class RegisterApplicantView(generics.CreateAPIView):
#     serializer_class   = ApplicantRegistrationSerializer
#     permission_classes = [AllowAny]

#     def create(self, request, *args, **kwargs):
#         try:
#             # 1) validate & save the new user
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)
#             user = serializer.save()

#             # 2) assign default Role "Applicant"
#             default_role, _ = Role.objects.get_or_create(name="Applicant")
#             UserRole.objects.create(user=user, role=default_role)
#             user.is_auth_user = True
#             user.save(update_fields=["is_auth_user"])

#             # 3) issue JWTs
#             refresh = RefreshToken.for_user(user)

#             # 4) build user payload
#             profile   = getattr(user, 'profile', None)
#             image_url = None
#             if profile and profile.profile_image:
#                 image_url = request.build_absolute_uri(profile.profile_image.url)

#             user_data = {
#                 "id":            user.id,
#                 "name":          user.full_name,
#                 "email":         user.email,
#                 "gender":        user.get_gender_display(),
#                 "mobile":        user.mobile,
#                 "organization":  user.organization,
#                 "role":          default_role.name,
#                 "profile_image": image_url,
#                 "created_at":    user.created_at.isoformat(),
#                 "is_verified":   user.is_verified,
#                 "is_active":     user.is_active,
#             }

#             return Response({
#                 "status":           "success",
#                 "response_message": "User registered successfully",
#                 "user":             user_data,
#                 "access_token":     str(refresh.access_token),
#                 "refresh_token":    str(refresh),
#             }, status=status.HTTP_201_CREATED)

#         except DRFValidationError as exc:
#             return Response({
#                 "status":           "error",
#                 "response_message": exc.detail
#             }, status=status.HTTP_400_BAD_REQUEST)

#         except DjangoValidationError as exc:
#             return Response({
#                 "status":           "error",
#                 "response_message": exc.message_dict
#             }, status=status.HTTP_400_BAD_REQUEST)

#         except Exception:
#             return Response({
#                 "status":           "error",
#                 "response_message": "Registration failed due to an internal error."
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from .serializers import ApplicantRegistrationSerializer
from .models import Role, UserRole  # Update import as per your project
from rest_framework.exceptions import AuthenticationFailed, ValidationError as DRFValidationError





def flatten_errors(detail):
    # For single key like "non_field_errors", just show its value
    if isinstance(detail, dict):
        if list(detail.keys()) == ["non_field_errors"]:
            errors = detail["non_field_errors"]
            # Customization:
            if isinstance(errors, list) and any("Invalid credentials" in str(e) for e in errors):
                return "Invalid email or password."  # <--- Your custom message here
            elif isinstance(errors, list):
                return " ".join(str(e) for e in errors)
            return str(errors)
        # Otherwise, flatten all fields/messages
        messages = []
        for field, errors in detail.items():
            if isinstance(errors, list):
                for error in errors:
                    messages.append(f"{field}: {error}")
            else:
                messages.append(f"{field}: {errors}")
        return " | ".join(messages)
    elif isinstance(detail, list):
        return " | ".join([str(e) for e in detail])
    return str(detail)




class RegisterApplicantView(generics.CreateAPIView):
    serializer_class = ApplicantRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            # Assign default Role "Applicant"
            default_role, _ = Role.objects.get_or_create(name="Applicant")
            UserRole.objects.create(user=user, role=default_role)
            user.is_auth_user = True
            user.save(update_fields=["is_auth_user"])

            # Issue JWTs
            refresh = RefreshToken.for_user(user)

            # Build user payload
            profile = getattr(user, 'profile', None)
            image_url = None
            if profile and getattr(profile, 'profile_image', None):
                image_url = request.build_absolute_uri(profile.profile_image.url)

            user_data = {
                "id":            user.id,
                "name":          user.full_name,
                "email":         user.email,
                "gender":        user.get_gender_display() if hasattr(user, 'get_gender_display') else user.gender,
                "mobile":        user.mobile,
                "organization":  user.organization,
                "role":          default_role.name,
                "profile_image": image_url,
                "created_at":    user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                "is_verified":   user.is_verified,
                "is_active":     user.is_active,
            }

            return Response({
                "status":           "success",
                "response_message": "User registered successfully",
                "user":             user_data,
                "access_token":     str(refresh.access_token),
                "refresh_token":    str(refresh),
            }, status=status.HTTP_201_CREATED)

        except DRFValidationError as exc:
            errors = exc.detail
            message = ""
            if isinstance(errors, dict):
                for field, msgs in errors.items():
                    if isinstance(msgs, list):
                        for msg in msgs:
                            message += f"{field.capitalize()}: {msg} "
                    else:
                        message += f"{field.capitalize()}: {msgs} "
            elif isinstance(errors, list):
                message = " ".join(str(m) for m in errors)
            else:
                message = str(errors)

            return Response({
                "status":           "error",
                "response_message": message.strip()
            }, status=status.HTTP_400_BAD_REQUEST)

        except DjangoValidationError as exc:
            return Response({
                "status":           "error",
                "response_message": exc.message_dict
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status":           "error",
                "response_message": "Registration failed due to an internal error."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class   = LoginSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']

            # issue tokens + login
            refresh = RefreshToken.for_user(user)
            access  = refresh.access_token
            django_login(request, user)

            # core user_data
            primary_role = user.roles.first()
            perms_from_roles = user.roles.prefetch_related('permissions') \
                                 .values_list('permissions__codename', flat=True)
            perms_direct     = user.user_permissions.values_list('codename', flat=True)
            permissions      = list(set(perms_direct) | set(perms_from_roles))

            # Check profile completion status
            profile_status = self.get_profile_status(user)

            user_data = {
                "id":            user.id,
                "email":         user.email,
                "name":          user.full_name,
                "gender":        user.get_gender_display(),
                "mobile":        user.mobile,
                "organization":  user.organization,
                "role":          primary_role.name if primary_role else None,
                "role_id":       primary_role.id   if primary_role else None,
                "permissions":   permissions,
                "profile_image": None,
                "created_at":    user.created_at.isoformat(),
                "last_login":    user.last_login.isoformat() if user.last_login else None,
                "is_verified":   user.is_verified,
                "is_active":     user.is_active,
                "profile_status": profile_status,  # Add profile status here
            }

            # evaluator committees
            if primary_role and primary_role.name.lower() == 'evaluator': 
                committees = []
    
                for c in ScreeningCommittee.objects.filter(head=user, is_active=True):
                    committees.append({
                    "committee_name": c.name,
                    "member_type": "Head",
                    "email": c.head.email if c.head else None
                    })
    
                for c in ScreeningCommittee.objects.filter(sub_head=user, is_active=True):
                    committees.append({
                    "committee_name": c.name,
                    "member_type": "Sub-head",
                    "email": c.sub_head.email if c.sub_head else None
                    })

                for cm in CommitteeMember.objects.filter(user=user, is_active=True):
                    committees.append({
                    "committee_name": cm.committee.name,
                    "member_type": "Member",
                    "email": cm.user.email if cm.user else None
                     })                

                user_data['committees'] = committees

            return Response({
                "status":           "success",
                "response_message": "Logged in successfully",
                "access_token":     str(access),
                "refresh_token":    str(refresh),
                "user":             user_data
            }, status=status.HTTP_200_OK)

        except AuthenticationFailed as exc:
            return Response({
                "status":           "error",
                "response_message": flatten_errors(exc.detail)
            }, status=status.HTTP_401_UNAUTHORIZED)

        except DRFValidationError as exc:
            return Response({
                "status":           "error",
                "response_message": flatten_errors(exc.detail)
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as exc:
            logger.error(f"Unexpected error in LoginView: {exc}")
            return Response({
                "status":           "error",
                "response_message": "Login failed due to an internal error."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def get_profile_status(self, user):
        """Check if user profile is complete based on required fields"""
        try:
            profile = getattr(user, 'profile', None)
            if not profile:
                return "incomplete"
            
            # Define required fields for profile completion
            required_fields = [
                # Basic Info from User model
                ('user', 'full_name'),
                ('user', 'email'), 
                ('user', 'mobile'),
                ('user', 'gender'),
                ('user', 'organization'),
                
                # Profile model fields
                ('profile', 'profile_image'),
                ('profile', 'dob'),
                ('profile', 'qualification'),
                ('profile', 'specialization'),
                ('profile', 'resume'),
                ('profile', 'applicant_type'),
                ('profile', 'applicant_aadhar'),
                ('profile', 'applicant_passport'),
                ('profile', 'address_line_1'),
                ('profile', 'street_village'),
                ('profile', 'city'),
                ('profile', 'state'),
                ('profile', 'country'),
                ('profile', 'pincode'),
                ('profile', 'company_mobile_no'),
                ('profile', 'landline_number'),
                ('profile', 'website_link'),
                ('profile', 'organization_registration_certificate'),
                ('profile', 'approval_certificate'),
                ('profile', 'three_years_financial_report'),
                ('profile', 'share_holding_pattern'),
                ('profile', 'dsir_certificate'),
                ('profile', 'id_type'),
                ('profile', 'id_number'),
            ]
            
            # Check each required field
            for source, field_name in required_fields:
                if source == 'user':
                    value = getattr(user, field_name, None)
                else:  # profile
                    value = getattr(profile, field_name, None)
                
                # Check if field is empty (None, empty string, or empty file)
                if not value or (hasattr(value, 'name') and not value.name):
                    return "incomplete"
            
            # Check boolean field separately
            if not hasattr(profile, 'is_organization_domestic'):
                return "incomplete"
                
            return "completed"
            
        except Exception as e:
            logger.error(f"Error checking profile status: {str(e)}")
            return "incomplete"



from rest_framework.permissions import IsAdminUser  # Or your custom admin check
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class AdminChangeUserPasswordView(APIView):
    permission_classes = [IsAdminUser]  # Restrict to admins

    def post(self, request):
        serializer = AdminChangeUserPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "status": "error",
                "response_message": "User with this email does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        user.set_password(new_password)
        user.save()

        return Response({
            "status": "success",
            "response_message": f"Password for {user.email} changed successfully."
        }, status=status.HTTP_200_OK)



    
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        # Check old password
        if not user.check_password(old_password):
            return Response(
                {"old_password": "Wrong password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)




class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class   = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception:
            return Response({
                "status":           "error",
                "response_message": "Could not fetch profile."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except (DRFValidationError, DjangoValidationError) as exc:
            return Response({
                "status":           "error",
                "response_message": exc.detail if hasattr(exc, 'detail') else exc.message_dict
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({
                "status":           "error",
                "response_message": "Profile update failed."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoleViewSet(viewsets.ModelViewSet):
    queryset            = Role.objects.all()
    serializer_class    = RoleSerializer
    permission_classes  = [IsAuthenticated, DjangoModelPermissions]

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except DRFValidationError as exc:
            return Response({"status":"error","response_message":exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"status":"error","response_message":"Role creation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except DRFValidationError as exc:
            return Response({"status":"error","response_message":exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"status":"error","response_message":"Role update failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception:
            return Response({"status":"error","response_message":"Role deletion failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AccountUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        return AdminBulkUserCreateSerializer if self.action == 'create' else UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
        except DRFValidationError as exc:
            return Response({"status":"error","response_message":exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoValidationError as exc:
            return Response({"status":"error","response_message":exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": "success",
            "response_message": "User created successfully",
            "user": UserSerializer(user, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='assign-role')
    def assign_role(self, request, pk=None):
        serializer = AssignRoleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Role assigned.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='assign-permission')
    def assign_permission(self, request, pk=None):
        serializer = AssignPermissionSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Permission assigned.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='subusers')
    def create_subuser(self, request):
        serializer = SubAuthUserSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Sub-user created.'}, status=status.HTTP_201_CREATED)


class PasswordResetRequestView(AuditMixin, generics.GenericAPIView):
    serializer_class     = PasswordResetRequestSerializer
    permission_classes   = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user       = User.objects.get(email=serializer.validated_data['email'])
        uidb64     = urlsafe_base64_encode(force_bytes(user.pk))
        token      = password_reset_token.make_token(user)
        reset_link = f"{request.scheme}://{request.get_host()}/password-reset-confirm/{uidb64}/{token}/"
        send_mail("Password Reset", f"Link: {reset_link}", None, [user.email])
        return Response({'detail':'Email sent.'})


class PasswordResetConfirmView(AuditMixin, generics.GenericAPIView):
    serializer_class     = PasswordResetConfirmSerializer
    permission_classes   = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail':'Password reset successful.'})


class AssignRoleView(AuditMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class AssignPermissionView(AuditMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = AssignPermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class ChangeUserRoleView(AuditMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangeUserRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class EvaluatorUserListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        evaluators = User.objects.filter(roles__name='Evaluator').select_related('profile').distinct()
        serializer = EvaluatorUserSerializer(evaluators, many=True)
        return Response(serializer.data)
    

class InitialSignupView(generics.CreateAPIView):
    """POST /initial-signup/ - Initial signup with basic data"""
    serializer_class = InitialSignupSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Assign default role
            default_role, _ = Role.objects.get_or_create(name="User")
            UserRole.objects.create(user=user, role=default_role)
            user.is_auth_user = True
            user.save(update_fields=["is_auth_user"])
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            user_data = {
                "id": user.id,
                "name": user.full_name,
                "email": user.email,
                "gender": user.get_gender_display(),
                "mobile": user.mobile,
                "organization": user.organization,
                "role": default_role.name,
                "created_at": user.created_at.isoformat(),
                "is_verified": user.is_verified,
                "is_active": user.is_active,
                "profile_completed": False
            }
            
            return Response({
                "status": "success",
                "response_message": "Initial signup successful",
                "user": user_data,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            return Response({
                "status": "error",
                "response_message": f"Signup failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetProfileView(APIView):
    """GET /get-profile/ - Get complete profile data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile, _ = Profile.objects.get_or_create(user=request.user)
            serializer = ProfileGetSerializer(profile)
            
            return Response({
                "status": "success",
                "response_message": "Profile data retrieved successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Get profile error: {str(e)}")
            return Response({
                "status": "error",
                "response_message": f"Could not fetch profile data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateProfileView(APIView):
    """POST /update-profile/ - Update profile based on payload"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            profile, _ = Profile.objects.get_or_create(user=request.user)
            
            # Update only fields that are in the payload
            serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            # Return updated data
            response_serializer = ProfileGetSerializer(profile)
            
            return Response({
                "status": "success",
                "response_message": "Profile updated successfully",
                "data": response_serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Update profile error: {str(e)}")
            return Response({
                "status": "error",
                "response_message": f"Profile update failed: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileStatusView(APIView):
    """GET /profile-status/ - Check profile completion status"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = getattr(request.user, 'profile', None)
            if not profile:
                return Response({
                    "status": "success",
                    "completion_percentage": 0,
                    "is_complete": False,
                    "missing_fields": ["Profile not created"]
                })
            
            # Define required fields for completion
            required_fields = [
                'profile_image', 'dob', 'qualification', 'specialization',
                'address_line_1', 'city', 'state', 'country', 'pincode',
                'applicant_type', 'resume'
            ]
            
            completed_fields = []
            missing_fields = []
            
            for field in required_fields:
                value = getattr(profile, field, None)
                if value:
                    completed_fields.append(field)
                else:
                    missing_fields.append(field)
            
            completion_percentage = (len(completed_fields) / len(required_fields)) * 100
            is_complete = completion_percentage == 100
            
            return Response({
                "status": "success",
                "completion_percentage": round(completion_percentage, 2),
                "is_complete": is_complete,
                "completed_fields": completed_fields,
                "missing_fields": missing_fields,
                "total_required": len(required_fields),
                "completed_count": len(completed_fields)
            })
            
        except Exception as e:
            logger.error(f"Profile status error: {str(e)}")
            return Response({
                "status": "error",
                "response_message": f"Could not check profile completion status: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class SubmissionDetailView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get proposal ID from request data
            proposal_id = request.data.get('proposalId')
            
            if not proposal_id:
                return Response({
                    "status": "error",
                    "response_message": "proposalId is required in request payload"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the submission by proposal_id
            submission = get_object_or_404(FormSubmission, proposal_id=proposal_id)
            
            # Build response data
            submission_data = {
                "proposalId": submission.proposal_id,
                "subject": submission.subject or "",
                "fundsRequested": float(submission.grants_from_ttdf) if submission.grants_from_ttdf else 0,
                "call": submission.service.name if submission.service else "",
                "submissionDate": submission.created_at.strftime("%Y-%m-%d") if submission.created_at else "",
                "applicationDocument": request.build_absolute_uri(submission.applicationDocument.url) if submission.applicationDocument else "",
                "initial_contri_applicant": float(submission.applicant_contribution) if submission.applicant_contribution else 0,
                "revised_contri_applicant": 0,  # Add this field to model if needed
                "initial_grant_from_ttdf": float(submission.grants_from_ttdf) if submission.grants_from_ttdf else 0,
                "revised_grant_from_ttdf": 0,  # Add this field to model if needed
                "expected_source_contribution": float(submission.expected_source_contribution) if submission.expected_source_contribution else None,
                "details_source_funding": float(submission.details_source_funding) if submission.details_source_funding else None,
            }
            
            return Response({
                "status": "success",
                "response_message": "Submission details retrieved successfully",
                "data": submission_data
            }, status=status.HTTP_200_OK)
            
        except FormSubmission.DoesNotExist:
            return Response({
                "status": "error",
                "response_message": f"No submission found with proposal ID: {proposal_id}"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error retrieving submission details: {str(e)}")
            return Response({
                "status": "error",
                "response_message": f"Could not retrieve submission details: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class AllSubmissionsView(APIView):
   
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get all submissions for the authenticated user that have shortlisted presentations
            submissions = FormSubmission.objects.filter(
                applicant=request.user,
                presentations__final_decision='shortlisted'  # Only shortlisted presentations
            ).distinct().order_by('-created_at')
            
            # Build response data for each submission
            submissions_list = []
            
            for submission in submissions:
                # Get the shortlisted presentation for additional info
                shortlisted_presentation = submission.presentations.filter(
                    final_decision='shortlisted'
                ).first()
                
                submission_data = {
                    "proposalId": submission.proposal_id,
                    "subject": submission.subject or "",
                    "fundsRequested": float(submission.grants_from_ttdf) if submission.grants_from_ttdf else 0,
                    "call": submission.service.name if submission.service else "",
                    "submissionDate": submission.created_at.strftime("%Y-%m-%d") if submission.created_at else "",
                    "applicationDocument": request.build_absolute_uri(submission.applicationDocument.url) if submission.applicationDocument else "",
                    "initial_contri_applicant": float(submission.applicant_contribution) if submission.applicant_contribution else 0,
                    "revised_contri_applicant": 0,  # Add this field to model if needed
                    "initial_grant_from_ttdf": float(submission.grants_from_ttdf) if submission.grants_from_ttdf else 0,
                    "revised_grant_from_ttdf": 0,  # Add this field to model if needed
                    "expected_source_contribution": float(submission.expected_source_contribution) if submission.expected_source_contribution else None,
                    "details_source_funding": float(submission.details_source_funding) if submission.details_source_funding else None,
                    
                    # Additional useful fields
                    "status": submission.get_status_display(),
                    "statusCode": submission.status,
                    "formId": submission.form_id,
                    "lastUpdated": submission.updated_at.strftime("%Y-%m-%d") if submission.updated_at else "",
                    "canEdit": submission.can_edit(),
                    
                    # Presentation specific fields
                    "presentationStatus": "shortlisted",
                    "presentationId": shortlisted_presentation.id if shortlisted_presentation else None,
                    "presentationDate": shortlisted_presentation.presentation_date.strftime("%Y-%m-%d %H:%M") if shortlisted_presentation and shortlisted_presentation.presentation_date else None,
                    "evaluatorMarks": float(shortlisted_presentation.evaluator_marks) if shortlisted_presentation and shortlisted_presentation.evaluator_marks else None,
                    "adminRemarks": shortlisted_presentation.admin_remarks if shortlisted_presentation else "",
                    "shortlistedAt": shortlisted_presentation.admin_evaluated_at.strftime("%Y-%m-%d %H:%M") if shortlisted_presentation and shortlisted_presentation.admin_evaluated_at else None,
                }
                submissions_list.append(submission_data)
            
            return Response({
                "status": "success",
                "response_message": f"Retrieved {len(submissions_list)} shortlisted submissions successfully",
                "count": len(submissions_list),
                "filter": "Only proposals shortlisted in presentation stage",
                "data": submissions_list
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error retrieving shortlisted submissions: {str(e)}")
            return Response({
                "status": "error",
                "response_message": f"Could not retrieve shortlisted submissions: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


