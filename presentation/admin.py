from django.contrib import admin
from django.utils.html import format_html
from .models import Presentation


@admin.register(Presentation)
class PresentationAdmin(admin.ModelAdmin):
    list_display = (
       # 'id',
        'proposal_id_display',
        'applicant_display',
        'evaluator_display',
        'video_file_status',
        'video_link_display',
        'is_ready_for_evaluation',
        'document_status',
        'presentation_date',
        'evaluator_marks',
        'is_ready_for_evaluation',
        'is_evaluation_completed',
        'final_decision',
        'admin_decision_display',
        'created_at',
    )
    list_filter = (
    'document_uploaded',
    'final_decision',
    'presentation_date',
    'created_at',
)

    search_fields = (
        'proposal__proposal_id',
        'applicant__email',
        'evaluator__email',
        'admin__email',
    )
    readonly_fields = (
        'created_at',                          
        'updated_at',
        # 'evaluated_at',
        'admin_evaluated_at',
    )
    ordering = ('-created_at',)

    def proposal_id_display(self, obj):
        return obj.proposal.proposal_id if obj.proposal else '-'
    proposal_id_display.short_description = "Proposal ID"

    def applicant_display(self, obj):
        return obj.applicant.get_full_name() if obj.applicant else '-'
    applicant_display.short_description = "Applicant"

    def evaluator_display(self, obj):
        return obj.evaluator.get_full_name() if obj.evaluator else '-'
    evaluator_display.short_description = "Evaluator"

    def admin_decision_display(self, obj):
        return obj.admin.get_full_name() if obj.admin else '-'
    admin_decision_display.short_description = "Admin"

    def video_file_status(self, obj):
        if obj.video:
            return format_html('<span style="color: green;">✔ file</span>')
        return format_html('<span style="color: red;">✘</span>')
    video_file_status.short_description = "Video File"

    def video_link_display(self, obj):
        if obj.video_link:
            return format_html('<a href="{}" target="_blank">Link</a>', obj.video_link)
        return format_html('<span style="color: red;">✘</span>')
    video_link_display.short_description = "Video Link"

    def document_status(self, obj):
        if obj.document:
            return format_html('<span style="color: green;">✔</span>')
        return format_html('<span style="color: red;">✘</span>')
    document_status.short_description = "Document"

