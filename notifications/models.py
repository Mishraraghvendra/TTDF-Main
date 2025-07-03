# notifications/models.py
from django.db import models
from django.conf import settings

class Notification(models.Model):
    event_id = models.CharField(max_length=100, unique=True, null=True, blank=True)  # For idempotency (Kafka)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='general')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.recipient} at {self.created_at}"

