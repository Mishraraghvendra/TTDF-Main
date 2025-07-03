# audit 
import uuid
from django.db import models
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

class ActivityLog(models.Model):
    ACTIONS = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login',  'Login'),
    )

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action      = models.CharField(max_length=20, choices=ACTIONS)
    app_label   = models.CharField(max_length=100)
    model_name  = models.CharField(max_length=100)
    object_pk   = models.CharField(max_length=255, null=True, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)
    # Use DjangoJSONEncoder to handle datetimes if they ever sneak through:
    changes     = models.JSONField(
        null=True,
        blank=True,
        encoder=DjangoJSONEncoder,
        help_text="Snapshot of model fields at time of action"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['app_label']),
            models.Index(fields=['model_name']),
        ]

    def __str__(self):
        return (
            f"{self.timestamp:%Y-%m-%d %H:%M:%S} | "
            f"{self.user or 'SYSTEM'} | {self.action.upper()} | "
            f"{self.app_label}.{self.model_name} → {self.object_repr}"
        )
