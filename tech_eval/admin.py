# tech_eval/admin.py - 

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    TechnicalEvaluationRound,
    EvaluatorAssignment,
    CriteriaEvaluation,
    EvaluationAuditLog,
    TRLAnalysis
)


class EvaluatorAssignmentInline(admin.TabularInline):
    model = EvaluatorAssignment
    extra = 0
    readonly_fields = [
        'assigned_at', 'completed_at', 'cached_percentage_score', 
        'cached_raw_marks', 'cached_max_marks', 'cached_criteria_count'
    ]
    fields = [
        'evaluator', 'is_completed', 'expected_trl', 'conflict_of_interest', 
        'cached_percentage_score', 'cached_criteria_count', 'assigned_at'
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('evaluator').only(
            'id', 'evaluator__full_name', 'evaluator__email', 'is_completed',
            'expected_trl', 'conflict_of_interest', 'cached_percentage_score',
            'cached_criteria_count', 'assigned_at'
        )


class CriteriaEvaluationInline(admin.TabularInline):
    model = CriteriaEvaluation
    extra = 0
    readonly_fields = ['cached_percentage', 'cached_weighted_score', 'evaluated_at']
    fields = ['evaluation_criteria', 'marks_given', 'cached_percentage', 'cached_weighted_score', 'evaluated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('evaluation_criteria').only(
            'id', 'evaluation_criteria__name', 'marks_given', 'cached_percentage',
            'cached_weighted_score', 'evaluated_at'
        )


@admin.register(TechnicalEvaluationRound)
class TechnicalEvaluationRoundAdmin(admin.ModelAdmin):
    list_display = [
        'proposal_display', 'assignment_status', 'overall_decision', 
        'cached_evaluators_count', 'cached_completion_status', 'cached_average_display',
        'progress_bar', 'created_at'
    ]
    list_filter = ['assignment_status', 'overall_decision', 'created_at']
    search_fields = ['proposal__proposal_id', 'cached_proposal_data']
    readonly_fields = [
        'created_at', 'updated_at', 'cache_updated_at',
        'cached_assigned_count', 'cached_completed_count', 'cached_average_percentage',
        'cached_marks_summary_display', 'cached_evaluator_data_display',
        'cached_proposal_data_display'
    ]
    inlines = [EvaluatorAssignmentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('proposal', 'assignment_status', 'overall_decision', 'assigned_by')
        }),
        ('Cached Performance Data', {
            'fields': (
                'cached_assigned_count', 'cached_completed_count', 'cached_average_percentage',
                'cached_marks_summary_display', 'cached_evaluator_data_display'
            ),
            'classes': ('collapse',)
        }),
        ('Cached Proposal Data', {
            'fields': ('cached_proposal_data_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'cache_updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['update_cached_values', 'export_to_excel']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('proposal', 'proposal__applicant').only(
            'id', 'assignment_status', 'overall_decision', 'created_at',
            'cached_assigned_count', 'cached_completed_count', 'cached_average_percentage',
            'proposal__proposal_id', 'proposal__applicant__organization'
        )
    
    def proposal_display(self, obj):
        """Display proposal with cached data if available"""
        if obj.cached_proposal_data:
            proposal_id = obj.cached_proposal_data.get('proposal_id', 'N/A')
            subject = obj.cached_proposal_data.get('subject', 'N/A')
            org_name = obj.cached_proposal_data.get('org_name', 'N/A')
        else:
            proposal_id = getattr(obj.proposal, 'proposal_id', 'N/A') if obj.proposal else 'N/A'
            subject = 'N/A'
            org_name = getattr(obj.proposal.applicant, 'organization', 'N/A') if obj.proposal and obj.proposal.applicant else 'N/A'
        
        return format_html(
            '<strong>{}</strong><br/><small>{}</small><br/><small style="color: #666;">{}</small>',
            proposal_id,
            subject[:50] + ('...' if len(subject) > 50 else ''),
            org_name
        )
    proposal_display.short_description = 'Proposal Details'
    
    def cached_evaluators_count(self, obj):
        """Display cached evaluator count"""
        return obj.cached_assigned_count
    cached_evaluators_count.short_description = 'Evaluators'
    cached_evaluators_count.admin_order_field = 'cached_assigned_count'
    
    def cached_completion_status(self, obj):
        """Display completion status using cached data"""
        completed = obj.cached_completed_count
        total = obj.cached_assigned_count
        
        if total == 0:
            return format_html('<span style="color: #999;">No evaluators</span>')
        
        percentage = round((completed / total) * 100, 1) if total > 0 else 0
        
        if percentage == 100:
            color = '#28a745'  # Green
            icon = '✓'
        elif percentage > 50:
            color = '#ffc107'  # Yellow
            icon = '◐'
        else:
            color = '#dc3545'  # Red
            icon = '○'
        
        return format_html(
            '<span style="color: {};">{} {}/{} ({}%)</span>',
            color, icon, completed, total, percentage
        )
    cached_completion_status.short_description = 'Completion'
    
    def cached_average_display(self, obj):
        """Display cached average percentage"""
        if obj.cached_average_percentage is not None:
            avg = obj.cached_average_percentage
            if avg >= 80:
                color = '#28a745'  # Green
            elif avg >= 60:
                color = '#ffc107'  # Yellow
            else:
                color = '#dc3545'  # Red
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, avg
            )
        return format_html('<span style="color: #999;">N/A</span>')
    cached_average_display.short_description = 'Avg Score'
    cached_average_display.admin_order_field = 'cached_average_percentage'
    
    def progress_bar(self, obj):
        """Visual progress bar using cached data"""
        if obj.cached_assigned_count == 0:
            return format_html('<span style="color: #999;">No evaluators</span>')
        
        percentage = round((obj.cached_completed_count / obj.cached_assigned_count) * 100, 1)
        
        if percentage == 100:
            bar_color = '#28a745'
        elif percentage > 50:
            bar_color = '#ffc107'
        else:
            bar_color = '#dc3545'
        
        return format_html(
            '<div style="width: 100px; background: #e9ecef; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; height: 20px; background: {}; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px;">'
            '{}%</div></div>',
            percentage, bar_color, percentage
        )
    progress_bar.short_description = 'Progress'
    
    def cached_marks_summary_display(self, obj):
        """Display cached marks summary in readable format"""
        if obj.cached_marks_summary:
            summary = obj.cached_marks_summary
            html = f"<strong>Average:</strong> {summary.get('average_percentage', 0)}%<br/>"
            html += f"<strong>Evaluators:</strong> {summary.get('total_evaluators', 0)}<br/>"
            
            individual_marks = summary.get('individual_marks', [])
            if individual_marks:
                html += "<strong>Individual Scores:</strong><br/>"
                for mark in individual_marks[:3]:  # Show first 3
                    html += f"• {mark.get('evaluator_name', 'Unknown')}: {mark.get('percentage', 0)}%<br/>"
                if len(individual_marks) > 3:
                    html += f"... and {len(individual_marks) - 3} more"
            
            return format_html(html)
        return "No cached data"
    cached_marks_summary_display.short_description = 'Marks Summary'
    
    def cached_evaluator_data_display(self, obj):
        """Display cached evaluator data in readable format"""
        if obj.cached_evaluator_data:
            evaluators = obj.cached_evaluator_data
            html = f"<strong>Total Evaluators:</strong> {len(evaluators)}<br/>"
            
            completed = [e for e in evaluators if e.get('is_completed')]
            html += f"<strong>Completed:</strong> {len(completed)}<br/>"
            
            conflicts = [e for e in evaluators if e.get('conflict_of_interest')]
            if conflicts:
                html += f"<strong>Conflicts:</strong> {len(conflicts)}<br/>"
            
            if evaluators:
                html += "<strong>Evaluators:</strong><br/>"
                for evaluator in evaluators[:3]:  # Show first 3
                    status = "✓" if evaluator.get('is_completed') else "○"
                    html += f"• {status} {evaluator.get('name', 'Unknown')}<br/>"
                if len(evaluators) > 3:
                    html += f"... and {len(evaluators) - 3} more"
            
            return format_html(html)
        return "No cached data"
    cached_evaluator_data_display.short_description = 'Evaluator Data'
    
    def cached_proposal_data_display(self, obj):
        """Display cached proposal data in readable format"""
        if obj.cached_proposal_data:
            data = obj.cached_proposal_data
            html = f"<strong>ID:</strong> {data.get('proposal_id', 'N/A')}<br/>"
            html += f"<strong>Call:</strong> {data.get('call', 'N/A')}<br/>"
            html += f"<strong>Org Type:</strong> {data.get('org_type', 'N/A')}<br/>"
            html += f"<strong>Organization:</strong> {data.get('org_name', 'N/A')}<br/>"
            html += f"<strong>Subject:</strong> {data.get('subject', 'N/A')[:100]}<br/>"
            html += f"<strong>Contact:</strong> {data.get('contact_person', 'N/A')}<br/>"
            html += f"<strong>Email:</strong> {data.get('contact_email', 'N/A')}<br/>"
            
            return format_html(html)
        return "No cached data"
    cached_proposal_data_display.short_description = 'Proposal Data'
    
    def update_cached_values(self, request, queryset):
        """Admin action to update cached values"""
        updated = 0
        for obj in queryset:
            obj.update_cached_values()
            updated += 1
        
        self.message_user(request, f'Updated cached values for {updated} evaluation rounds.')
    update_cached_values.short_description = "Update cached values"
    
    def export_to_excel(self, request, queryset):
        """Admin action to export data"""
        # This would implement Excel export functionality
        self.message_user(request, f'Excel export functionality can be implemented here.')
    export_to_excel.short_description = "Export to Excel"


# @admin.register(EvaluatorAssignment)
# class EvaluatorAssignmentAdmin(admin.ModelAdmin):
#     list_display = [
#         'evaluator_name', 'proposal_display', 'is_completed', 
#         'cached_score_display', 'expected_trl', 'conflict_status', 'assigned_at'
#     ]
#     list_filter = ['is_completed', 'conflict_of_interest', 'expected_trl']
#     search_fields = ['evaluator__full_name', 'evaluator__email']
#     readonly_fields = [
#         'assigned_at', 'completed_at', 'cached_raw_marks', 
#         'cached_max_marks', 'cached_percentage_score', 'cached_criteria_count',
#         'cached_criteria_data_display'
#     ]
#     inlines = [CriteriaEvaluationInline]
    
#     fieldsets = (
#         ('Assignment Details', {
#             'fields': ('evaluation_round', 'evaluator', 'is_completed')
#         }),
#         ('TRL Assessment', {
#             'fields': ('current_trl', 'expected_trl')
#         }),
#         ('Conflict of Interest', {
#             'fields': ('conflict_of_interest', 'conflict_remarks')
#         }),
#         ('Cached Performance Data', {
#             'fields': (
#                 'cached_raw_marks', 'cached_max_marks', 'cached_percentage_score',
#                 'cached_criteria_count', 'cached_criteria_data_display'
#             ),
#             'classes': ('collapse',)
#         }),
#         ('Comments & Timestamps', {
#             'fields': ('overall_comments', 'assigned_at', 'completed_at')
#         }),
#     )
    
#     actions = ['update_cached_values']
    
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related(
#             'evaluator', 'evaluation_round__proposal'
#         ).only(
#             'id', 'is_completed', 'expected_trl', 'conflict_of_interest', 'assigned_at',
#             'cached_percentage_score', 'cached_criteria_count',
#             'evaluator__full_name', 'evaluator__email',
#             'evaluation_round__proposal__proposal_id'
#         )
    
#     def evaluator_name(self, obj):
#         return obj.evaluator.get_full_name()
#     evaluator_name.short_description = 'Evaluator'
#     evaluator_name.admin_order_field = 'evaluator__full_name'
    
#     def proposal_display(self, obj):
#         proposal_id = getattr(obj.evaluation_round.proposal, 'proposal_id', 'N/A')
#         return proposal_id
#     proposal_display.short_description = 'Proposal'
    
#     def cached_score_display(self, obj):
#         """Display cached score with visual indicators"""
#         if obj.is_completed and obj.cached_percentage_score is not None:
#             score = obj.cached_percentage_score
#             criteria_count = obj.cached_criteria_count
            
#             if score >= 80:
#                 color = '#28a745'  # Green
#                 icon = '🟢'
#             elif score >= 60:
#                 color = '#ffc107'  # Yellow
#                 icon = '🟡'
#             else:
#                 color = '#dc3545'  # Red
#                 icon = '🔴'
            
#             return format_html(
#                 '{} <span style="color: {}; font-weight: bold;">{:.1f}%</span><br/>'
#                 '<small>{} criteria</small>',
#                 icon, color, score, criteria_count
#             )
#         elif obj.is_completed:
#             return format_html('<span style="color: #dc3545;">No cached data</span>')
#         else:
#             return format_html('<span style="color: #999;">Not completed</span>')
#     cached_score_display.short_description = 'Score'
    
#     def conflict_status(self, obj):
#         if obj.conflict_of_interest:
#             return format_html('<span style="color: #dc3545;">⚠️ Conflict</span>')
#         return format_html('<span style="color: #28a745;">✓ Clear</span>')
#     conflict_status.short_description = 'Conflict'
    
#     def cached_criteria_data_display(self, obj):
#         """Display cached criteria data"""
#         if obj.cached_criteria_data:
#             criteria_list = obj.cached_criteria_data
#             html = f"<strong>Total Criteria:</strong> {len(criteria_list)}<br/>"
            
#             for criteria in criteria_list[:5]:  # Show first 5
#                 name = criteria.get('criteria_name', 'Unknown')
#                 marks = criteria.get('marks_given', 0)
#                 max_marks = criteria.get('max_marks', 0)
#                 percentage = criteria.get('percentage', 0)
                
#                 html += f"• {name}: {marks}/{max_marks} ({percentage}%)<br/>"
            
#             if len(criteria_list) > 5:
#                 html += f"... and {len(criteria_list) - 5} more criteria"
            
#             return format_html(html)
#         return "No cached data"
#     cached_criteria_data_display.short_description = 'Criteria Breakdown'
    
#     def update_cached_values(self, request, queryset):
#         """Admin action to update cached values"""
#         updated = 0
#         for obj in queryset:
#             obj.update_cached_values()
#             updated += 1
        
#         self.message_user(request, f'Updated cached values for {updated} assignments.')
#     update_cached_values.short_description = "Update cached values"

 # Ensure this exists and is correct

@admin.register(EvaluatorAssignment)
class EvaluatorAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'evaluator_name', 'proposal_display', 'is_completed',
        'cached_score_display', 'expected_trl', 'conflict_status', 'assigned_at'
    ]
    list_filter = ['is_completed', 'conflict_of_interest', 'expected_trl']
    search_fields = ['evaluator__full_name', 'evaluator__email']
    readonly_fields = [
        'assigned_at', 'completed_at', 'cached_raw_marks',
        'cached_max_marks', 'cached_percentage_score', 'cached_criteria_count',
        'cached_criteria_data_display'
    ]
    inlines = [CriteriaEvaluationInline]

    fieldsets = (
        ('Assignment Details', {
            'fields': ('evaluation_round', 'evaluator', 'is_completed')
        }),
        ('TRL Assessment', {
            'fields': ('current_trl', 'expected_trl')
        }),
        ('Conflict of Interest', {
            'fields': ('conflict_of_interest', 'conflict_remarks')
        }),
        ('Cached Performance Data', {
            'fields': (
                'cached_raw_marks', 'cached_max_marks', 'cached_percentage_score',
                'cached_criteria_count', 'cached_criteria_data_display'
            ),
            'classes': ('collapse',)
        }),
        ('Comments & Timestamps', {
            'fields': ('overall_comments', 'assigned_at', 'completed_at')
        }),
    )

    actions = ['update_cached_values']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'evaluator', 'evaluation_round__proposal'
        ).only(
            'id', 'is_completed', 'expected_trl', 'conflict_of_interest', 'assigned_at',
            'cached_percentage_score', 'cached_criteria_count',
            'evaluator__full_name', 'evaluator__email',
            'evaluation_round__proposal__proposal_id'
        )

    @admin.display(description='Evaluator', ordering='evaluator__full_name')
    def evaluator_name(self, obj):
        return obj.evaluator.get_full_name()

    @admin.display(description='Proposal')
    def proposal_display(self, obj):
        return getattr(obj.evaluation_round.proposal, 'proposal_id', 'N/A')


    @admin.display(description='Score')
    def cached_score_display(self, obj):
        """Display cached score with visual indicators"""
        if obj.is_completed and obj.cached_percentage_score is not None:
            try:
                # Explicitly cast to float
                score = float(obj.cached_percentage_score)
            except (TypeError, ValueError):
                score = 0.0

            criteria_count = obj.cached_criteria_count or 0

            if score >= 80:
                color = '#28a745'  # Green
                icon = '🟢'
            elif score >= 60:
                color = '#ffc107'  # Yellow
                icon = '🟡'
            else:
                color = '#dc3545'  # Red
                icon = '🔴'

            # Format score safely as float
            formatted_score = "{:.1f}".format(score)

            return format_html(
                '{} <span style="color: {}; font-weight: bold;">{}%</span><br/>'
                '<small>{} criteria</small>',
                icon, color, formatted_score, criteria_count
            )
        elif obj.is_completed:
            return format_html('<span style="color: #dc3545;">No cached data</span>')
        else:
            return format_html('<span style="color: #999;">Not completed</span>')



    @admin.display(description='Conflict')
    def conflict_status(self, obj):
        if obj.conflict_of_interest:
            return format_html('<span style="color: #dc3545;">⚠️ Conflict</span>')
        return format_html('<span style="color: #28a745;">✓ Clear</span>')

    @admin.display(description='Criteria Breakdown')
    def cached_criteria_data_display(self, obj):
        """Display cached criteria data"""
        if obj.cached_criteria_data:
            criteria_list = obj.cached_criteria_data
            html = f"<strong>Total Criteria:</strong> {len(criteria_list)}<br/>"

            for criteria in criteria_list[:5]:  # Limit to 5 for readability
                name = criteria.get('criteria_name', 'Unknown')
                marks = criteria.get('marks_given', 0)
                max_marks = criteria.get('max_marks', 0)
                percentage = criteria.get('percentage', 0)
                html += f"• {name}: {marks}/{max_marks} ({percentage}%)<br/>"

            if len(criteria_list) > 5:
                html += f"... and {len(criteria_list) - 5} more criteria"

            return format_html(html)
        return "No cached data"

    @admin.action(description="Update cached values")
    def update_cached_values(self, request, queryset):
        updated = 0
        for obj in queryset:
            obj.update_cached_values()
            updated += 1
        self.message_user(request, f'Updated cached values for {updated} assignments.')


@admin.register(CriteriaEvaluation)
class CriteriaEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        'evaluation_criteria', 'evaluator_name', 'marks_display', 
        'cached_percentage_display', 'cached_weighted_display', 'evaluated_at'
    ]
    list_filter = ['evaluation_criteria', 'evaluated_at']
    search_fields = [
        'evaluation_criteria__name', 
        'evaluator_assignment__evaluator__full_name',
        'evaluator_assignment__evaluator__email'
    ]
    readonly_fields = ['cached_percentage', 'cached_weighted_score', 'evaluated_at']
    
    fieldsets = (
        ('Evaluation Details', {
            'fields': ('evaluator_assignment', 'evaluation_criteria', 'marks_given', 'remarks')
        }),
        ('Cached Calculations', {
            'fields': ('cached_percentage', 'cached_weighted_score'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('evaluated_at',)
        }),
    )
    
    actions = ['update_cached_values']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'evaluator_assignment__evaluator', 'evaluation_criteria'
        ).only(
            'id', 'marks_given', 'cached_percentage', 'cached_weighted_score', 'evaluated_at',
            'evaluator_assignment__evaluator__full_name',
            'evaluator_assignment__evaluator__email',
            'evaluation_criteria__name', 'evaluation_criteria__total_marks'
        )
    
    def evaluator_name(self, obj):
        return obj.evaluator_assignment.evaluator.get_full_name()
    evaluator_name.short_description = 'Evaluator'
    
    def marks_display(self, obj):
        max_marks = obj.evaluation_criteria.total_marks
        return f"{obj.marks_given}/{max_marks}"
    marks_display.short_description = 'Marks'
    
    def cached_percentage_display(self, obj):
        if obj.cached_percentage is not None:
            try:
                percentage = float(obj.cached_percentage)
                if percentage >= 80:
                    color = '#28a745'
                elif percentage >= 60:
                    color = '#ffc107'
                else:
                    color = '#dc3545'

                formatted_percentage = f"{percentage:.1f}%"
                return format_html(
                    '<span style="color: {}; font-weight: bold;">{}</span>',
                    color, formatted_percentage
                )
            except (TypeError, ValueError):
                return "Invalid data"
        return "No cache"


    cached_percentage_display.short_description = 'Percentage'
    
    def cached_weighted_display(self, obj):
        if obj.cached_weighted_score is not None:
            return f"{obj.cached_weighted_score:.2f}"
        return "No cache"
    cached_weighted_display.short_description = 'Weighted Score'
    
    def update_cached_values(self, request, queryset):
        """Admin action to update cached values"""
        updated = 0
        for obj in queryset:
            obj.update_cached_values()
            updated += 1
        
        self.message_user(request, f'Updated cached values for {updated} criteria evaluations.')
    update_cached_values.short_description = "Update cached values"


@admin.register(EvaluationAuditLog)

class EvaluationAuditLogAdmin(admin.ModelAdmin):
    list_display = ['evaluation_round', 'action', 'user', 'description_short', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['evaluation_round__proposal__proposal_id', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('evaluation_round', 'action', 'user', 'description')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def description_short(self, obj):
        return obj.description[:100] + ('...' if len(obj.description) > 100 else '')
    description_short.short_description = 'Description'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'evaluation_round')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TRLAnalysis)
class TRLAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'evaluation_round', 'consensus_expected_trl', 'trl_consensus_level', 
        'trl_variance_display', 'updated_at'
    ]
    list_filter = ['trl_consensus_level', 'consensus_expected_trl']
    search_fields = ['evaluation_round__proposal__proposal_id']
    readonly_fields = ['created_at', 'updated_at', 'cached_analysis_summary_display']
    
    fieldsets = (
        ('TRL Consensus', {
            'fields': ('evaluation_round', 'consensus_current_trl', 'consensus_expected_trl')
        }),
        ('Consensus Metrics', {
            'fields': ('trl_variance', 'trl_consensus_level')
        }),
        ('Analysis', {
            'fields': ('analysis_notes', 'cached_analysis_summary_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['calculate_consensus']
    
    def trl_variance_display(self, obj):
        if obj.trl_variance is not None:
            variance = obj.trl_variance
            if variance <= 0.5:
                color = '#28a745'  # Green
                icon = '🟢'
            elif variance <= 1.5:
                color = '#ffc107'  # Yellow
                icon = '🟡'
            else:
                color = '#dc3545'  # Red
                icon = '🔴'
            
            return format_html(
                '{} <span style="color: {};">{:.2f}</span>',
                icon, color, variance
            )
        return "N/A"
    trl_variance_display.short_description = 'Variance'
    
    def cached_analysis_summary_display(self, obj):
        if obj.cached_analysis_summary:
            summary = obj.cached_analysis_summary
            html = f"<strong>Mean TRL:</strong> {summary.get('mean_trl', 0):.1f}<br/>"
            html += f"<strong>Variance:</strong> {summary.get('variance', 0):.2f}<br/>"
            html += f"<strong>Consensus:</strong> {summary.get('consensus_level', 'Unknown')}<br/>"
            html += f"<strong>Total Evaluators:</strong> {summary.get('total_evaluators', 0)}<br/>"
            
            distribution = summary.get('trl_distribution', {})
            if distribution:
                html += "<strong>TRL Distribution:</strong><br/>"
                for trl, count in distribution.items():
                    html += f"• TRL {trl}: {count} evaluators<br/>"
            
            return format_html(html)
        return "No cached analysis"
    cached_analysis_summary_display.short_description = 'Analysis Summary'
    
    def calculate_consensus(self, request, queryset):
        """Admin action to calculate TRL consensus"""
        updated = 0
        for obj in queryset:
            obj.calculate_consensus()
            updated += 1
        
        self.message_user(request, f'Calculated consensus for {updated} TRL analyses.')
    calculate_consensus.short_description = "Calculate TRL consensus"


# Custom admin site configuration
admin.site.site_header = 'Technical Evaluation Administration'
admin.site.site_title = 'Tech Eval Admin'
admin.site.index_title = 'Technical Evaluation Management'