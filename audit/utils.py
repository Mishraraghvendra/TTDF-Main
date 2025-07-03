# audit/utils.py
from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog

def log_admin_action(user, action, instance):
    ct = ContentType.objects.get_for_model(instance.__class__)
    ActivityLog.objects.create(
        user        = user,
        action      = action,
        app_label   = ct.app_label,
        model_name  = ct.model,
        object_pk   = str(getattr(instance, instance._meta.pk.name)),
        object_repr = str(instance),
        changes     = None,   # or capture a snapshot if you like
    )
