from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile, Role, RolePermission, UserRole, UserPermission, SubAuthUser, SubUserPermission
from audit.signals import log_model_save, log_model_delete

User = get_user_model()
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

# Remove automatic ProfileInline to avoid duplicate Profile creation (handled by signal)
class UserRoleInline(admin.TabularInline):
    model = UserRole
    fk_name = 'user'
    extra = 1

class UserPermissionInline(admin.TabularInline):
    model = UserPermission
    fk_name = 'user'
    extra = 1

class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    fk_name = 'role'
    extra = 1

class SubUserPermissionInline(admin.TabularInline):
    model = SubUserPermission
    fk_name = 'subuser'
    extra = 1

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Omit ProfileInline to let signal create the profile automatically
    inlines = (UserRoleInline, UserPermissionInline)
    list_display = ('id','email','full_name','mobile','is_applicant','is_auth_user','is_staff','is_superuser',)
    list_filter = ('is_applicant','is_auth_user','is_staff','is_superuser','gender')
    search_fields = ('email','full_name','mobile')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields':('email','password')}),
        ('Personal Info', {'fields':('full_name','mobile','gender','organization')}),
        ('Permissions', {'fields':('is_active','is_staff','is_superuser','is_applicant','is_auth_user','groups','user_permissions')}),
        ('Important dates', {'fields':('last_login',)}),
    )
    add_fieldsets = (
        (None, {'classes':('wide',),'fields':('email','mobile','full_name','password1','password2')}),
    )

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user','dob','specialization',)
    search_fields = ('user__email',)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    inlines = (RolePermissionInline,)
    list_display = ('name','description')
    search_fields = ('name',)

@admin.register(SubAuthUser)
class SubAuthUserAdmin(admin.ModelAdmin):
    inlines = (SubUserPermissionInline,)
    list_display = ('user','created_by','role')
    search_fields = ('user__email','created_by__email')



# For audit log only
@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Force an audit entry with the real admin user:
        log_model_save(sender=obj.__class__, instance=obj, created=not change)

    def delete_model(self, request, obj):
        log_model_delete(sender=obj.__class__, instance=obj)
        super().delete_model(request, obj)   