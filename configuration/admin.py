# configuration/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    Service, ServiceForm, EvaluationStage, 
    EvaluationCriteriaConfig, EvaluatorAssignment,
    Application, ApplicationStageProgress,
    ScreeningCommittee, CommitteeMember, ScreeningResult
)




# @admin.register(Service)
# class ServiceAdmin(admin.ModelAdmin):
#     list_display = ('name', 'is_active', 'created_by', 'created_at')
#     list_filter = ('is_active',)
#     search_fields = ('name', 'description')
#     readonly_fields = ('created_at', 'updated_at')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'status', 'is_active', 'start_date', 'end_date', 'schedule_date', 
        'created_by', 'created_at'
    )
    list_filter = ('is_active', 'status', 'start_date', 'end_date')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'is_active', 'created_by')
    fieldsets = (
        (None, {
            'fields': (
                'name', 'description', 'status', 'is_active',
                'start_date', 'end_date', 'schedule_date',
                'image', 'documents', 'created_by', 'created_at', 'updated_at',
            )
        }),
    )


@admin.register(ServiceForm)
class ServiceFormAdmin(admin.ModelAdmin):
    list_display = ('service', 'is_active', 'created_at')
    list_filter = ('is_active', 'service')
    # search_fields = ('service__name', 'form_template__title')
    readonly_fields = ('created_at',)


@admin.register(ScreeningCommittee)
class ScreeningCommitteeAdmin(admin.ModelAdmin):
    list_display = ("name", "committee_type", "is_created", "is_active", "created_at")
    list_filter = ("committee_type", "is_active", "is_created")
    search_fields = ("name", "description")
    

@admin.register(CommitteeMember)
class CommitteeMemberAdmin(admin.ModelAdmin):
    list_display = ('committee', 'user', 'is_active', 'assigned_by', 'assigned_at')
    list_filter = ('committee', 'is_active')
    search_fields = ('committee__name', 'user__username')
    readonly_fields = ('assigned_at',)


@admin.register(ScreeningResult)
class ScreeningResultAdmin(admin.ModelAdmin):
    list_display = ('application', 'committee', 'result', 'screened_by', 'screened_at')
    list_filter = ('result', 'committee')
    search_fields = ('application__applicant__username', 'committee__name')
    readonly_fields = ('screened_at',)


@admin.register(EvaluationStage)
class EvaluationStageAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'order', 'cutoff_marks', 'is_active')
    list_filter = ('service', 'is_active')
    search_fields = ('name', 'service__name')
    readonly_fields = ('created_at',)
    ordering = ('service', 'order')


@admin.register(EvaluationCriteriaConfig)
class EvaluationCriteriaConfigAdmin(admin.ModelAdmin):
    list_display = ('stage', 'criteria_type', 'total_marks', 'weight')
    list_filter = ('stage', 'criteria_type')
    search_fields = ('stage__name', 'field__label')
    readonly_fields = ('created_at',)


@admin.register(EvaluatorAssignment)
class EvaluatorAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'stage', 'assigned_by', 'assigned_at', 'is_active')
    list_filter = ('stage', 'is_active')
    search_fields = ('user__username', 'stage__name')
    readonly_fields = ('assigned_at',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'service', 'status', 'submitted_at', 'current_stage')
    list_filter = ('status', 'service', 'current_stage')
    search_fields = ('applicant__username', 'service__name')
    readonly_fields = ('submitted_at',)


@admin.register(ApplicationStageProgress)
class ApplicationStageProgressAdmin(admin.ModelAdmin):
    list_display = ('application', 'stage', 'status', 'start_date', 'completion_date', 'total_score')
    list_filter = ('status', 'stage')
    search_fields = ('application__applicant__username', 'stage__name')
    readonly_fields = ('start_date', 'completion_date')

    