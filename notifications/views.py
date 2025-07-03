from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to view and interact with their notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filter notifications by 'unread' query param.
        GET /api/notifications/?unread=1  -> only unread notifications
        """
        qs = Notification.objects.filter(recipient=self.request.user).order_by('-created_at')
        unread = self.request.query_params.get("unread")
        if unread in ("1", "true", "yes"):
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a single notification as read.
        POST /api/notifications/<id>/mark_read/
        """
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'notification marked as read'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Bulk mark all notifications as read for this user.
        POST /api/notifications/mark_all_read/
        """
        updated = Notification.objects.filter(recipient=self.request.user, is_read=False).update(is_read=True)
        return Response({'status': f'{updated} notifications marked as read'}, status=status.HTTP_200_OK)
