# notifications/admin.py
from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message', 'notification_type', 'event_id', 'created_at', 'is_read')

    list_filter = ('is_read', 'created_at')
