from .models import Notification

def send_notification(recipient, message, notification_type="general"):
    Notification.objects.create(
        recipient=recipient,
        message=message,
        notification_type=notification_type
    )
