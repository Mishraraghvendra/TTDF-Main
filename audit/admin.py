from django.contrib import admin
from .models import ActivityLog

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display  = (
        'timestamp','user','action','app_label',
        'model_name','object_pk','object_repr'
    )
    list_filter   = ('action','app_label','model_name','user')
    search_fields = ('object_pk','object_repr','changes')
    ordering      = ('-timestamp',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(user__isnull=True) 
