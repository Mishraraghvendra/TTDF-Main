import logging
from django.db import transaction
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.validators import URLValidator


from .models import (
    User, Profile, Role, UserRole, UserPermission,
    SubAuthUser, SubUserPermission
)
from .tokens import password_reset_token


# Applicant Registration
class ApplicantRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = User
        fields = ["email","mobile","full_name","gender","organization","password"]

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            mobile=validated_data["mobile"],
            password=validated_data["password"],
            full_name=validated_data.get("full_name",""),
            gender=validated_data.get("gender","O"),
            organization=validated_data.get("organization",""),
            is_applicant=True,
        )


# Login
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type':'password'})

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise ValidationError("Invalid credentials.")
        if not user.is_active:
            raise ValidationError("User account is disabled.")
        data['user'] = user
        return data


# Change Password
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)




class AdminChangeUserPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)




# Profile
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['address','dob','additional_info','specialization']


    def validate_website_link(self, value):
        if value and not value.startswith(('http://', 'https://')):
            value = 'https://' + value
        return value       


# Roles
class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Role
        fields = ['id','name','description','permissions']

    def validate_permissions(self, perms):
        invalid = [c for c in perms if not Permission.objects.filter(codename=c).exists()]
        if invalid:
            raise ValidationError(f"Invalid permissions: {invalid}")
        return perms

    def create(self, validated_data):
        perms = validated_data.pop('permissions', [])
        with transaction.atomic():
            role = Role.objects.create(**validated_data)
            qs = Permission.objects.filter(codename__in=perms)
            role.permissions.set(qs)
        return role


# Assign Role & Permission
class AssignRoleSerializer(serializers.Serializer):
    email       = serializers.EmailField()
    role        = serializers.CharField()
    designation = serializers.CharField(required=False, allow_blank=True)
    expertise   = serializers.CharField(required=False, allow_blank=True)
    department  = serializers.CharField(required=False, allow_blank=True)
    subject     = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        try:
            data['user'] = User.objects.get(email=data['email'])
        except User.DoesNotExist:
            raise ValidationError("User not found.")
        try:
            data['role_obj'] = Role.objects.get(name=data['role'])
        except Role.DoesNotExist:
            raise ValidationError("Role not found.")
        if UserRole.objects.filter(user=data['user'], role=data['role_obj']).exists():
            raise ValidationError("Role already assigned.")
        return data

    def create(self, validated_data):
        user = validated_data['user']
        role = validated_data['role_obj']
        ur = UserRole.objects.create(
            user=user, role=role,
            designation=validated_data.get('designation', ''),
            expertise=validated_data.get('expertise', ''),
            department=validated_data.get('department', ''),
            subject=validated_data.get('subject', '')
        )
        user.is_auth_user = True
        user.save(update_fields=['is_auth_user'])
        return ur



class AssignPermissionSerializer(serializers.Serializer):
    email      = serializers.EmailField()
    permission = serializers.CharField()

    def validate(self, data):
        try:
            data['user'] = User.objects.get(email=data['email'])
        except User.DoesNotExist:
            raise ValidationError("User not found.")
        try:
            data['perm_obj'] = Permission.objects.get(codename=data['permission'])
        except Permission.DoesNotExist:
            raise ValidationError("Permission not found.")
        if UserPermission.objects.filter(
            user=data['user'], permission=data['perm_obj']
        ).exists():
            raise ValidationError("Permission already assigned.")
        return data

    def create(self, validated_data):
        UserPermission.objects.create(
            user=validated_data['user'],
            permission=validated_data['perm_obj']
        )
        return validated_data['user']


# SubAuthUser
class SubAuthUserSerializer(serializers.Serializer):
    email        = serializers.EmailField()
    mobile       = serializers.CharField(max_length=15)
    full_name    = serializers.CharField(max_length=100)
    password     = serializers.CharField(write_only=True)
    role         = serializers.CharField()
    permissions  = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, data):
        creator = self.context['request'].user
        if User.objects.filter(email=data['email']).exists():
            raise ValidationError("Email already in use.")
        try:
            data['role_obj'] = Role.objects.get(name=data['role'])
        except Role.DoesNotExist:
            raise ValidationError("Role not found.")
        invalid = []
        for cd in data.get('permissions', []):
            try:
                perm = Permission.objects.get(codename=cd)
            except Permission.DoesNotExist:
                invalid.append(cd)
                continue
            if not (creator.user_permissions.filter(pk=perm.pk).exists() or
                    creator.roles.filter(permissions=perm).exists()):
                invalid.append(cd)
        if invalid:
            raise ValidationError(f"Cannot grant: {invalid}")
        return data

    def create(self, validated_data):
        creator  = self.context['request'].user
        perms    = validated_data.pop('permissions', [])
        role_obj = validated_data.pop('role_obj')
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data['email'],
                mobile=validated_data['mobile'],
                password=validated_data['password'],
                full_name=validated_data['full_name'],
                is_applicant=False,
                is_auth_user=True
            )
            SubAuthUser.objects.create(
                created_by=creator, user=user, role=role_obj
            )
            UserRole.objects.create(user=user, role=role_obj)
            sub_perms = [
                SubUserPermission(
                    subuser=SubAuthUser.objects.get(user=user),
                    permission=Permission.objects.get(codename=cd)
                ) for cd in perms
            ]
            SubUserPermission.objects.bulk_create(sub_perms)
        return user


# Password Reset
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    def validate_email(self, email):
        if not User.objects.filter(email=email, is_active=True).exists():
            raise ValidationError("No active account with this email.")
        return email



class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64   = serializers.CharField()
    token    = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        try:
            uid  = force_str(urlsafe_base64_decode(data['uidb64']))
            user = User.objects.get(pk=uid, is_active=True)
        except Exception:
            raise ValidationError("Invalid uid.")
        if not password_reset_token.check_token(user, data['token']):
            raise ValidationError("Invalid or expired token.")
        data['user'] = user
        return data

    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['password'])
        user.save(update_fields=['password'])
        return user
 

# UserRoleDetail for nested output
class UserRoleDetailSerializer(serializers.ModelSerializer):
    role        = serializers.CharField(source='role.name', read_only=True)
    role_id     = serializers.IntegerField(source='role.id', read_only=True)
    designation = serializers.CharField(required=False, allow_blank=True)
    expertise   = serializers.CharField(required=False, allow_blank=True)
    department  = serializers.CharField(required=False, allow_blank=True)
    subject     = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model  = UserRole
        fields = ['id','role','role_id','designation','expertise','department','subject']


class UserSerializer(serializers.ModelSerializer):
    # flat writable fields
    name         = serializers.CharField(source='full_name', required=True)
    email        = serializers.EmailField(required=True)
    mobile       = serializers.CharField(required=True)
    gender       = serializers.ChoiceField(choices=User.GENDER_CHOICES, required=True)
    organization = serializers.CharField(allow_blank=True, required=False)

    # allow incoming status/role for PATCH
    status       = serializers.CharField(write_only=True, required=False)
    role         = serializers.CharField(write_only=True, required=False)

    # nested, writable role-detail
    roles_detail = UserRoleDetailSerializer(source='user_roles', many=True, required=False)

    # read-only outputs
    profile_image = serializers.SerializerMethodField()
    created_at    = serializers.DateTimeField(read_only=True)
    updated_at    = serializers.DateTimeField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id','email','name','gender','mobile','organization',
            'status','role','roles_detail','profile_image','created_at','updated_at',
        ]
        read_only_fields = ['id','profile_image','created_at','updated_at']

    def to_representation(self, instance):
        data          = super().to_representation(instance)
        data['status'] = "Active" if instance.is_active else "Inactive"
        first_ur      = instance.user_roles.first()
        data['role']  = first_ur.role.name if first_ur else None
        return data

    def get_profile_image(self, obj):
        try:
            url = obj.profile.profile_image.url
        except (Profile.DoesNotExist, ValueError, AttributeError):
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(url)

    def validate_email(self, value):
        qs = User.objects.exclude(pk=self.instance.pk if self.instance else None)
        if qs.filter(email__iexact=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value

    def validate_mobile(self, value):
        qs = User.objects.exclude(pk=self.instance.pk if self.instance else None)
        if qs.filter(mobile=value).exists():
            raise serializers.ValidationError("User with this mobile already exists.")
        return value

    def update(self, instance, validated_data):
        # 1) status toggle
        status_str = validated_data.pop('status', None)
        if status_str is not None:
            instance.is_active = (status_str.lower() == "active")

        # 2) top-level role swap
        role_name = validated_data.pop('role', None)
        if role_name:
            try:
                role_obj = Role.objects.get(name=role_name)
            except Role.DoesNotExist:
                raise serializers.ValidationError({"role": f"Role '{role_name}' not found."})
            ur = instance.user_roles.first()
            if ur:
                ur.role = role_obj
                ur.save()
            else:
                UserRole.objects.create(user=instance, role=role_obj)

        # 3) nested roles_detail patch
        roles_data = validated_data.pop('user_roles', None)
        if roles_data:
            ur = instance.user_roles.first()
            if not ur:
                raise serializers.ValidationError({"roles_detail":"No role assigned to update."})
            detail = roles_data[0]
            for field in ('designation','expertise','department','subject'):
                if field in detail:
                    setattr(ur, field, detail[field])
            ur.save()

        # 4) remaining User fields
        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        # 5) validate & save
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        instance.save()
        return instance


class ChangeUserRoleSerializer(serializers.Serializer):
    email = serializers.EmailField()
    roles = serializers.ListField(child=serializers.CharField())

    def validate(self, data):
        try:
            data['user'] = User.objects.get(email=data['email'])
        except User.DoesNotExist:
            raise ValidationError("User not found.")
        role_objs, invalid = [], []
        for name in data['roles']:
            try:
                role_objs.append(Role.objects.get(name=name))
            except Role.DoesNotExist:
                invalid.append(name)
        if invalid:
            raise ValidationError(f"Roles not found: {invalid}")
        data['role_objs'] = role_objs
        return data

    def save(self):
        user = self.validated_data['user']
        user.roles.set(self.validated_data['role_objs'])
        user.is_auth_user = bool(self.validated_data['role_objs'])
        user.save(update_fields=['is_auth_user'])
        return user


class AdminBulkUserCreateSerializer(serializers.Serializer):
    name             = serializers.CharField(max_length=100)
    email            = serializers.EmailField()
    mobile           = serializers.CharField(max_length=15)
    password         = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    gender           = serializers.ChoiceField(choices=User.GENDER_CHOICES, default='O')

    designation      = serializers.CharField(required=False, allow_blank=True)
    role             = serializers.CharField()
    expertise        = serializers.CharField(required=False, allow_blank=True)
    department       = serializers.CharField(required=False, allow_blank=True)
    subject          = serializers.CharField(required=False, allow_blank=True)
    status           = serializers.ChoiceField(choices=[("Active","Active"),("Inactive","Inactive")])
    is_staff         = serializers.BooleanField(default=False)
    is_superuser     = serializers.BooleanField(default=False)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        try:
            data['role_obj'] = Role.objects.get(name=data['role'])
        except Role.DoesNotExist:
            raise serializers.ValidationError(f"Role '{data['role']}' not found.")
        return data

    def create(self, validated_data):
        name        = validated_data.pop('name')
        email       = validated_data.pop('email')
        mobile      = validated_data.pop('mobile')
        gender      = validated_data.pop('gender')
        pwd         = validated_data.pop('password')
        validated_data.pop('confirm_password')

        role_obj    = validated_data.pop('role_obj')
        designation = validated_data.pop('designation', '')
        expertise   = validated_data.pop('expertise', '')
        department  = validated_data.pop('department', '')
        subject     = validated_data.pop('subject', '')
        status_str  = validated_data.pop('status')
        is_staff     = validated_data.pop('is_staff', False)
        is_superuser = validated_data.pop('is_superuser', False)

        user = User.objects.create_user(
            email=email,
            mobile=mobile,
            password=pwd,
            full_name=name,
            gender=gender,
            is_active=(status_str=="Active"),
            is_applicant=False,
            is_auth_user=True,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )

        UserRole.objects.create(
            user=user,
            role=role_obj,
            designation=designation,
            expertise=expertise,
            department=department,
            subject=subject
        )

        return user


class EvaluatorUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='full_name') 
    profile = ProfileSerializer(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'mobile', 'organization','profile']


class InitialSignupSerializer(serializers.ModelSerializer):
    """Serializer for initial signup with only basic user fields"""
    name = serializers.CharField(max_length=100, source='full_name')
    gender = serializers.ChoiceField(choices=User.GENDER_CHOICES)
    mobile = serializers.CharField(max_length=15)
    email = serializers.EmailField()
    organization = serializers.CharField(max_length=100, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    confirmPassword = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['name', 'gender', 'mobile', 'email', 'organization', 'password', 'confirmPassword']
    
    def validate(self, data):
        if data['password'] != data['confirmPassword']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):
        
        validated_data.pop('confirmPassword')
        
        
        user = User.objects.create_user(**validated_data)
        
       
        Profile.objects.get_or_create(user=user)
        
        return user


# class ProfileUpdateSerializer(serializers.Serializer):
#     """Serializer for updating both User and Profile fields"""
    
#     # User fields (can be updated)
#     name = serializers.CharField(max_length=100, required=False, allow_blank=True)  
#     gender = serializers.ChoiceField(choices=User.GENDER_CHOICES, required=False)
#     mobile = serializers.CharField(max_length=15, required=False, allow_blank=True)
#     email = serializers.EmailField(required=False, allow_blank=True)
#     organization = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
#     # Profile fields (all existing fields)
#     profile_image = serializers.ImageField(required=False)
#     dob = serializers.DateField(required=False)
#     additional_info = serializers.JSONField(required=False)
#     specialization = serializers.CharField(max_length=100, required=False, allow_blank=True)
#     qualification = serializers.CharField(max_length=255, required=False, allow_blank=True)
#     applicant_official_email = serializers.EmailField(required=False, allow_blank=True)
#     proposal_duration_years = serializers.IntegerField(required=False)
#     proposal_duration_months = serializers.IntegerField(required=False)
#     proposal_submitted_by = serializers.CharField(max_length=255, required=False, allow_blank=True)
#     address_line_1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
#     address_line_2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
#     street_village = serializers.CharField(max_length=255, required=False, allow_blank=True)
#     city = serializers.CharField(max_length=100, required=False, allow_blank=True)
#     country = serializers.CharField(max_length=100, required=False, allow_blank=True)
#     state = serializers.CharField(max_length=100, required=False, allow_blank=True)
#     pincode = serializers.CharField(max_length=20, required=False, allow_blank=True)
#     landline_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
#     company_mobile_no = serializers.CharField(max_length=20, required=False, allow_blank=True)
#     # website_link = serializers.URLField(required=False, allow_blank=True)
#     website_link = serializers.CharField(required=False, allow_blank=True)
#     company_as_per_guidelines = serializers.CharField(max_length=255, required=False, allow_blank=True)
#     application_submission_date = serializers.DateField(required=False)
#     is_applied_before = serializers.BooleanField(required=False)
#     resume = serializers.FileField(required=False)
#     applicant_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
#     applicant_aadhar = serializers.CharField(max_length=12, required=False, allow_blank=True)
#     applicant_passport = serializers.CharField(max_length=20, required=False, allow_blank=True)
#     organization_registration_certificate = serializers.FileField(required=False)
#     approval_certificate = serializers.FileField(required=False)
#     three_years_financial_report = serializers.FileField(required=False)
#     is_organization_domestic = serializers.BooleanField(required=False)
#     share_holding_pattern = serializers.FileField(required=False)
#     dsir_certificate = serializers.FileField(required=False)
#     id_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
#     id_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
#     def update(self, instance, validated_data):
#         user = instance.user
        
#         # Update User fields if provided
#         user_fields = ['name', 'gender', 'mobile', 'email', 'organization','website_link'
# ]
#         for field in user_fields:
#             if field in validated_data:
#                 value = validated_data.pop(field)
#                 if field == 'name':
#                     setattr(user, 'full_name', value)
#                 else:
#                     setattr(user, field, value)
#         user.save()
        
#         # Update Profile fields
#         for field, value in validated_data.items():
#             setattr(instance, field, value)
#         instance.save()
        
#         return instance
    

#     def validate_website_link(self, value):
#         if value and not value.startswith(('http://', 'https://')):
#             value = 'https://' + value
#         # Validate final value is a URL
#         from django.core.validators import URLValidator
#         from django.core.exceptions import ValidationError as DjangoValidationError
#         validator = URLValidator()
#         try:
#             validator(value)
#         except DjangoValidationError:
#             raise serializers.ValidationError("Enter a valid URL.")
#         return value  


class ProfileUpdateSerializer(serializers.Serializer):
    # User fields (can be updated)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=User.GENDER_CHOICES, required=False)
    mobile = serializers.CharField(max_length=15, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    organization = serializers.CharField(max_length=100, required=False, allow_blank=True)

    # Profile fields (all existing fields)
    profile_image = serializers.ImageField(required=False)
    dob = serializers.DateField(required=False)
    additional_info = serializers.JSONField(required=False)
    specialization = serializers.CharField(max_length=100, required=False, allow_blank=True)
    qualification = serializers.CharField(max_length=255, required=False, allow_blank=True)
    applicant_official_email = serializers.EmailField(required=False, allow_blank=True)
    proposal_duration_years = serializers.IntegerField(required=False)
    proposal_duration_months = serializers.IntegerField(required=False)
    proposal_submitted_by = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_line_1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_line_2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    street_village = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    pincode = serializers.CharField(max_length=20, required=False, allow_blank=True)
    landline_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    company_mobile_no = serializers.CharField(max_length=20, required=False, allow_blank=True)
    website_link = serializers.CharField(required=False, allow_blank=True)  # <-- Use CharField!
    company_as_per_guidelines = serializers.CharField(max_length=255, required=False, allow_blank=True)
    application_submission_date = serializers.DateField(required=False)
    is_applied_before = serializers.BooleanField(required=False)
    resume = serializers.FileField(required=False)
    applicant_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    applicant_aadhar = serializers.CharField(max_length=12, required=False, allow_blank=True)
    applicant_passport = serializers.CharField(max_length=20, required=False, allow_blank=True)
    organization_registration_certificate = serializers.FileField(required=False)
    approval_certificate = serializers.FileField(required=False)
    three_years_financial_report = serializers.FileField(required=False)
    is_organization_domestic = serializers.BooleanField(required=False)
    share_holding_pattern = serializers.FileField(required=False)
    dsir_certificate = serializers.FileField(required=False)
    id_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    id_number = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_website_link(self, value):
        if value and not value.startswith(('http://', 'https://')):
            value = 'https://' + value
        if value:
            validator = URLValidator()
            try:
                validator(value)
            except DjangoValidationError:
                raise serializers.ValidationError("Enter a valid URL.")
        return value

    def update(self, instance, validated_data):
        user = instance.user

        # Update User fields if provided
        user_fields = ['name', 'gender', 'mobile', 'email', 'organization']
        for field in user_fields:
            if field in validated_data:
                value = validated_data.pop(field)
                if field == 'name':
                    setattr(user, 'full_name', value)
                else:
                    setattr(user, field, value)
        user.save()

        # Update Profile fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance




class ProfileGetSerializer(serializers.ModelSerializer):
    """Serializer for getting complete profile data"""
    # Include user fields for complete data
    email = serializers.CharField(source='user.email', read_only=True)
    mobile = serializers.CharField(source='user.mobile', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    gender = serializers.CharField(source='user.get_gender_display', read_only=True)
    organization = serializers.CharField(source='user.organization', read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            # User fields
            'email', 'mobile', 'full_name', 'gender', 'organization',
            # Profile fields
            'profile_image', 'dob', 'additional_info', 'specialization',
            'qualification', 'applicant_official_email', 'proposal_duration_years',
            'proposal_duration_months', 'proposal_submitted_by',
            'address_line_1', 'address_line_2', 'street_village', 'city',
            'country', 'state', 'pincode', 'landline_number', 'company_mobile_no',
            'website_link', 'company_as_per_guidelines', 'application_submission_date',
            'is_applied_before', 'resume', 'applicant_type', 'applicant_aadhar',
            'applicant_passport', 'organization_registration_certificate',
            'approval_certificate', 'three_years_financial_report',
            'is_organization_domestic', 'share_holding_pattern', 'dsir_certificate',
            'id_type', 'id_number','individualPAN', 'individualPanAttachment','tan_pan_cin'
        ]

    def validate_website_link(self, value):
        if value and not value.startswith(('http://', 'https://')):
            value = 'https://' + value
        return value    




class SimpleUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'full_name', 'email', 'role')  # <-- Only these fields are returned

    def get_role(self, obj):
        roles = obj.roles.all()
        return [r.name for r in roles] if roles else []
