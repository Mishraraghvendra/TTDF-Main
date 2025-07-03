from rest_framework import viewsets, permissions
from .models import ActivityLog
from .serializers import ActivityLogSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status





class AdminLogPagination(PageNumberPagination):
    page_size = 50        # Or whatever default you want
    page_size_query_param = 'page_size'  # Allow client to override with ?page_size=
    max_page_size = 200


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    
    queryset            = ActivityLog.objects.exclude(app_label='contenttypes').order_by('-timestamp')
    serializer_class    = ActivityLogSerializer
    permission_classes  = [permissions.IsAdminUser]
    filterset_fields    = ['user__username','action','app_label','model_name']
    search_fields       = ['object_pk','object_repr','changes']



# views.py

from rest_framework import generics, permissions, filters, viewsets
from django.contrib.auth import get_user_model
from audit.models import ActivityLog
from audit.serializers import ActivityLogSerializer
from .serializers import UserAuditSerializer  # (as above)

User = get_user_model()

class AdminUserListView(generics.ListAPIView):
    """
    Admin can view all users and their last login.
    """
    queryset = User.objects.all()
    serializer_class = UserAuditSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email']

class AdminUserDetailView(generics.RetrieveAPIView):
    """
    Admin can view a single user's details and last login.
    """
    queryset = User.objects.all()
    serializer_class = UserAuditSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'pk'

# audit/views.py

from rest_framework import viewsets, permissions
from .models import ActivityLog
from .serializers import ActivityLogSerializer
from django.utils import timezone
from datetime import timedelta

class AdminActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin can view audit logs. Filter by user (user=<id>), date range (start, end).
    Only shows last 30 days by default.
    """
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['user', 'action', 'app_label', 'model_name']
    search_fields = ['object_pk', 'object_repr', 'changes']
    pagination_class = AdminLogPagination 

    def get_queryset(self):
        qs = ActivityLog.objects.select_related('user').order_by('-timestamp')
        user_id = self.request.query_params.get('user')
        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')

        # Show last 30 days by default if no filters
        if not (user_id or start or end):
            qs = qs.filter(timestamp__gte=timezone.now() - timedelta(days=30))

        if user_id:
            qs = qs.filter(user_id=user_id)
        if start:
            qs = qs.filter(timestamp__gte=start)
        if end:
            qs = qs.filter(timestamp__lte=end)
        return qs



class LatestActivityLogsAPIView(APIView):
    """
    Admin-only API to fetch the latest N activity logs.
    Use ?limit=30 to set how many logs to return (default 50, max 200).
    """
    permission_classes = [IsAdminUser]

    def get(self, request, format=None):
        limit = request.query_params.get('limit')
        try:
            limit = int(limit) if limit else 50
            limit = max(1, min(limit, 200))  # Enforce 1 <= limit <= 200
        except ValueError:
            limit = 50

        logs = ActivityLog.objects.select_related('user').order_by('-timestamp')[:limit]
        serializer = ActivityLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)