# users/permissions.py

from rest_framework.permissions import BasePermission
from .models import UserRole

class IsSuperuserOrAdminRole(BasePermission):
    """
    Grants access if the user is a superuser OR has a UserRole named 'admin'.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return UserRole.objects.filter(user=user, role__name='admin').exists()
