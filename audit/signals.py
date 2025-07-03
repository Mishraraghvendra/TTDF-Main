# signals.py
from datetime import date, datetime
from django.db import transaction, models as django_models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields.files import FileField
from django.apps import apps
from django.db import connection

from .models import ActivityLog
from .middleware import get_current_user

SKIP_APPS = (
    'audit',
    'contenttypes',
    'auth',
    'sessions',
    'admin',
    'sites',
    'socialaccount',
)

def is_skipped(sender):
    label = sender._meta.app_label
    return label in SKIP_APPS or label.startswith('django')

def _really_log(user, action, sender, instance, snapshot):
    # Prevent logging if table does not exist
    try:
        # Table name may be quoted differently in some DBs
        table_names = connection.introspection.table_names()
        if 'audit_activitylog' not in table_names:
            return  # Don't log until the table exists
    except Exception:
        return

    ct = ContentType.objects.get_for_model(sender)
    try:
        object_repr = str(instance)
    except Exception:
        pk_name = instance._meta.pk.name
        object_repr = f"{ct.model} pk={getattr(instance, pk_name, 'unknown')}"

    ActivityLog.objects.create(
        user        = user,
        action      = action,
        app_label   = ct.app_label,
        model_name  = ct.model,
        object_pk   = str(getattr(instance, instance._meta.pk.name)),
        object_repr = object_repr,
        changes     = snapshot,
    )

@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    if is_skipped(sender):
        return

    try:
        user   = get_current_user()
        action = 'create' if created else 'update'

        snapshot = {}
        for field in instance._meta.fields:
            name = field.name
            val  = getattr(instance, name)

            if isinstance(field, django_models.DateField) or isinstance(field, django_models.DateTimeField):
                snapshot[name] = val.isoformat() if val else None
            elif isinstance(field, django_models.ForeignKey):
                snapshot[name] = str(val) if val else None
            elif isinstance(field, FileField):
                snapshot[name] = val.url if (val and hasattr(val, 'url')) else None
            else:
                snapshot[name] = val

        transaction.on_commit(
            lambda: _really_log(user, action, sender, instance, snapshot)
        )
    except Exception:
        pass

@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    if is_skipped(sender):
        return

    try:
        user = get_current_user()
        transaction.on_commit(
            lambda: _really_log(user, 'delete', sender, instance, None)
        )
    except Exception:
        pass
