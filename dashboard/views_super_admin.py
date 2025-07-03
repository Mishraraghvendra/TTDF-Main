from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission,Group
from rest_framework import status

User = get_user_model()

class PermissionManagementAPIView(APIView):
    """
    GET:    List all available permissions
    POST:   Assign permissions to user(s)
    DELETE: Remove permissions from user(s)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        permissions = Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'codename'
        )
        data = [
            {
                'id': perm.id,
                'codename': perm.codename,
                'name': perm.name,
                'app_label': perm.content_type.app_label,
                'model': perm.content_type.model,
            }
            for perm in permissions
        ]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Assign permissions to users.
        JSON:
        {
            "user_ids": [1, 2, ...],
            "permission_ids": [11, 12, ...]
        }
        """
        user_ids = request.data.get('user_ids', [])
        permission_ids = request.data.get('permission_ids', [])

        if not user_ids or not permission_ids:
            return Response(
                {"detail": "user_ids and permission_ids are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        users = User.objects.filter(id__in=user_ids)
        permissions = Permission.objects.filter(id__in=permission_ids)

        for user in users:
            user.user_permissions.add(*permissions)

        return Response(
            {"detail": f"Permissions assigned to {users.count()} user(s)."},
            status=status.HTTP_200_OK
        )

    def delete(self, request):
        """
        Remove permissions from users.
        JSON (in body):
        {
            "user_ids": [1, 2, ...],
            "permission_ids": [11, 12, ...]
        }
        """
        user_ids = request.data.get('user_ids', [])
        permission_ids = request.data.get('permission_ids', [])

        if not user_ids or not permission_ids:
            return Response(
                {"detail": "user_ids and permission_ids are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        users = User.objects.filter(id__in=user_ids)
        permissions = Permission.objects.filter(id__in=permission_ids)

        for user in users:
            user.user_permissions.remove(*permissions)

        return Response(
            {"detail": f"Permissions removed from {users.count()} user(s)."},
            status=status.HTTP_200_OK
        )


class RolePermissionsAPIView(APIView):
    """
    GET /api/role-permissions/?roles=admin,IA
    Returns permissions attached to the given roles (groups).
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        roles = request.query_params.get('roles')
        if not roles:
            return Response({"detail": "roles query param is required"}, status=400)
        role_names = [role.strip() for role in roles.split(',')]
        permissions = Permission.objects.none()
        for group in Group.objects.filter(name__in=role_names):
            permissions = permissions | group.permissions.all()
        permissions = permissions.distinct().select_related('content_type')

        data = [
            {
                'id': perm.id,
                'codename': perm.codename,
                'name': perm.name,
                'app_label': perm.content_type.app_label,
                'model': perm.content_type.model,
            }
            for perm in permissions
        ]
        return Response(data, status=200)