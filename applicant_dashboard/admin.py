# applicant_dashboard/admin.py
from django.contrib import admin
from .models import DashboardStats, UserActivity, DraftApplication


@admin.register(DashboardStats)
class DashboardStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_proposals', 'approved_proposals', 'under_evaluation', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['user__email', 'user__full_name']
    readonly_fields = ['last_updated']
    
    actions = ['refresh_stats']
    
    def refresh_stats(self, request, queryset):
        for stats in queryset:
            stats.refresh_stats()
        self.message_user(request, f"Refreshed stats for {queryset.count()} users.")
    refresh_stats.short_description = "Refresh selected stats"


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'activity_type', 'is_read', 'created_at']
    list_filter = ['activity_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'title', 'description']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'related_submission')


@admin.register(DraftApplication)
class DraftApplicationAdmin(admin.ModelAdmin):
    list_display = ['submission', 'user', 'progress_percentage', 'last_updated']
    list_filter = ['progress_percentage', 'last_updated']
    search_fields = ['user__email', 'submission__subject']
    readonly_fields = ['last_updated']
    
    actions = ['recalculate_progress']
    
    def recalculate_progress(self, request, queryset):
        for draft in queryset:
            draft.calculate_progress()
        self.message_user(request, f"Recalculated progress for {queryset.count()} drafts.")
    recalculate_progress.short_description = "Recalculate progress"