# users/models.py
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin,
    Group, Permission
)
from django.conf import settings


TTDF_COMPANY_CHOICES = [
    ('domestic_company', 'Domestic Company(ies) with focus on telecom R&D, Use case development'),
    ('startup_msme', 'Startups / MSMEs'),
    ('academic', 'Academic institutions'),
    ('rnd_section8_govt', 'R&D institutions, Section 8 companies / Societies, Central & State government entities / PSUs /Autonomous Bodies/SPVs / Limited liability partnerships'),
]

class UserManager(BaseUserManager):
    def _validate_email_mobile(self, email, mobile):
        if not email:
            raise ValueError("Users must have an email.")
        if not mobile:
            raise ValueError("Users must have a mobile number.")

    def create_user(self, email, mobile, password=None, **extra_fields):
        self._validate_email_mobile(email, mobile)
        email = self.normalize_email(email)
        user = self.model(email=email, mobile=mobile, **extra_fields)
        user.set_password(password or self.make_random_password())
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, mobile, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True")
        return self.create_user(email, mobile, password, **extra_fields)
 

class User(AbstractBaseUser, PermissionsMixin):
    GENDER_CHOICES = (('M', 'Male'), ('F', 'Female'), ('O', 'Other'))

    email        = models.EmailField(unique=True)
    mobile       = models.CharField(max_length=15, unique=True)
    full_name    = models.CharField(max_length=100)
    gender       = models.CharField(max_length=1, choices=GENDER_CHOICES)
    organization = models.CharField(max_length=100, blank=True)

    is_active    = models.BooleanField(default=True)
    is_staff     = models.BooleanField(default=False)
    is_applicant = models.BooleanField(default=True)
    is_auth_user = models.BooleanField(default=False)
    is_verified  = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name='users_groups',
        related_query_name='user_group',
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='users_user_permissions',
        related_query_name='user_permission',
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    roles = models.ManyToManyField(
        'Role', through='UserRole', related_name='users', blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['mobile', 'full_name', 'gender']

    objects = UserManager()

    def __str__(self):
        return self.email

    def get_full_name(self):
     return self.full_name.strip()


    @property
    def name(self):
        return self.full_name

    def has_role(self, role_name):
        return self.roles.filter(name=role_name).exists()

    @property
    def is_superadmin(self):
        return self.is_superuser

    @property
    def is_admin(self):
        return self.is_staff

    @property
    def is_evaluator(self):
        return self.has_role('Evaluator')

    @property
    def is_applicant_role(self):
        return self.has_role('Applicant')


class Profile(models.Model):
    user            = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    address         = models.TextField(blank=True)
    dob             = models.DateField(null=True, blank=True)
    additional_info = models.JSONField(blank=True, null=True)
    profile_image   = models.ImageField(upload_to='user/profiles/', blank=True, null=True)
    specialization =  models.CharField(max_length=100, blank=True,null=True)

    qualification = models.CharField(max_length=255, blank=True, null=True)
    applicant_official_email = models.EmailField(blank=True, null=True)
    proposal_duration_years = models.PositiveIntegerField(blank=True, null=True)
    proposal_duration_months = models.PositiveIntegerField(blank=True, null=True)
    proposal_submitted_by = models.CharField(max_length=255, blank=True, null=True)
    address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    street_village = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True) 
    pincode = models.CharField(max_length=20, blank=True, null=True)
    landline_number = models.CharField(max_length=20, blank=True, null=True)
    company_mobile_no = models.CharField(max_length=20, blank=True, null=True)
    website_link = models.URLField(blank=True, null=True)
    company_as_per_guidelines = models.CharField(max_length=255, blank=True, null=True)
    application_submission_date = models.DateField(blank=True, null=True)
    is_applied_before = models.BooleanField(default=False)

    resume = models.FileField(upload_to='user/resumes/', blank=True, null=True)
    applicant_type = models.CharField(max_length=100, blank=True, null=True)
    applicant_aadhar = models.CharField(max_length=12, blank=True, null=True)
    applicant_passport = models.CharField(max_length=20, blank=True, null=True)

    organization_registration_certificate = models.FileField(upload_to='org/certificates/', blank=True, null=True)
    approval_certificate = models.FileField(upload_to='org/approvals/', blank=True, null=True)
    three_years_financial_report = models.FileField(upload_to='org/financial/', blank=True, null=True)
    is_organization_domestic = models.BooleanField(default=True)
    share_holding_pattern = models.FileField(upload_to='org/shareholding/', blank=True, null=True)
    dsir_certificate = models.FileField(upload_to='org/dsir/', blank=True, null=True)

    id_type = models.CharField(max_length=50, blank=True, null=True)
    id_number = models.CharField(max_length=50, blank=True, null=True)

    companyAsPerCfp = models.CharField(max_length=1000,choices=TTDF_COMPANY_CHOICES,blank=True,null=True)
    individualPanAttachment =models.FileField(upload_to='Applicant Pan', blank=True, null=True)
    
    tan_pan_cin = models.FileField(upload_to='org/tan_pan_cin/', blank=True, null=True)
    def __str__(self):
        return f"Profile of {self.user.email}"
 

class Role(models.Model):
    name        = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name='roles'
    )

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role       = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['role', 'permission'], name='unique_role_permission')
        ]

    def __str__(self):
        return f"{self.role.name} → {self.permission.codename}"


class UserRole(models.Model):
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    role        = models.ForeignKey(Role, on_delete=models.CASCADE)
    designation = models.CharField(max_length=100, blank=True)
    expertise   = models.CharField(max_length=100, blank=True)
    department  = models.CharField(max_length=100, blank=True)
    subject     = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'role'], name='unique_user_role')
        ]

    def __str__(self):
        return f"{self.user.email} ∈ {self.role.name}"


class UserPermission(models.Model):
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_permissions_map'
    )
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'permission'], name='unique_user_permission')
        ]

    def __str__(self):
        return f"{self.user.email} ↦ {self.permission.codename}"


class SubAuthUser(models.Model):
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_sub_users'
    )
    user        = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sub_auth_profile'
    )
    role        = models.ForeignKey(Role, on_delete=models.CASCADE)
    permissions = models.ManyToManyField(
        Permission,
        through='SubUserPermission',
        related_name='subusers'
    )

    def __str__(self):
        return f"SubUser {self.user.email} by {self.created_by.email}"


class SubUserPermission(models.Model):
    subuser    = models.ForeignKey(SubAuthUser, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['subuser', 'permission'], name='unique_subuser_permission')
        ]

    def __str__(self):
        return f"{self.subuser.user.email} ↦ {self.permission.codename}"
