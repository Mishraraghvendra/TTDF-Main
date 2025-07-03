from django.contrib import admin

# Register your models here.

from .models import StaticForm

@admin.register(StaticForm)
class StaticFormAdmin(admin.ModelAdmin):
    list_display = ('form_id', 'proposal_id', 'user', 'service', 'status', 'created_at')
