# audit/drf.py

from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog

class AuditMixin:
    """
    DRF mixin to log create/retrieve/update/delete on ModelViewSets.
    Must be first in the inheritance list.
    """
    def finalize_response(self, request, response, *args, **kwargs):
        # Let DRF build the real response first
        resp = super().finalize_response(request, response, *args, **kwargs)

        # Only log on successful 200/201/204 for viewsets with a queryset
        if resp.status_code not in (200, 201, 204) or not hasattr(self, 'queryset') or self.queryset is None:
            return resp

        # Actor: your admin user from token auth
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            user_id   = user.id
            user_repr = str(user)
        else:
            user_id = None
            user_repr = None

        # What model are we dealing with?
        model_class = self.queryset.model
        ct = ContentType.objects.get_for_model(model_class)

        # Try to extract the PK of the object from resp.data
        obj_pk = None
        data = resp.data or {}
        if isinstance(data, dict):
            # common case: top-level id or pk
            obj_pk = data.get('id') or data.get('pk')
            # fallback: maybe nested under a "user" key, etc.
            if obj_pk is None and 'user' in data and isinstance(data['user'], dict):
                obj_pk = data['user'].get('id')

        # Try to get a human repr (calls your model's __str__())
        obj_repr = None
        if obj_pk is not None:
            try:
                instance = model_class.objects.get(pk=obj_pk)
                obj_repr = str(instance)
            except model_class.DoesNotExist:
                obj_repr = None

        # Record the log
        ActivityLog.objects.create(
            user        = user if user_id else None,
            action      = request.method.lower(),
            app_label   = ct.app_label,
            model_name  = ct.model,
            object_pk   = str(obj_pk) if obj_pk is not None else None,
            object_repr = obj_repr or "",
            changes     = {
                "endpoint":    request.get_full_path(),
                "status_code": resp.status_code,
                "user_repr":   user_repr,
            }
        )

        return resp
