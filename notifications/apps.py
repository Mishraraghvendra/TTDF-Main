# from django.apps import AppConfig


# class NotificationsConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'notifications'


# notifications/apps.py
from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        # Import signals so they are registered when Django starts.
        import notifications.signals
