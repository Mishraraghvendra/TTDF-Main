# app_eval/admin.py

from django.contrib import admin
from .models import (
    CriteriaType, Evaluator, EvaluationItem, 
    EvaluationAssignment, CriteriaEvaluation, 
    QuestionEvaluation, EvaluationCutoff,PassingRequirement
)
from dynamic_form.models import FormSubmission 

@admin.register(PassingRequirement)
class PassingRequirementAdmin(admin.ModelAdmin):
    list_display = ('id',
        'requirement_name',         
        'evaluation_min_passing', 
        'presentation_min_passing', 
        'presentation_max_marks',
        'final_status_min_passing',
        'status'  #service
    )
    list_filter = ['status', ]  #service
    search_fields = ['requirement_name', 'service__name']


# Add this class to show FormSubmission in app_eval admin
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ('form_id', 'proposal_id', 'subject', 'status')
    search_fields = ('form_id', 'proposal_id', 'subject')

class CriteriaTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

class EvaluatorAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')

class EvaluationItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'total_marks', 'weightage', 'status', 'type', 'memberType')
    list_filter = ('status', 'type', 'memberType')
    search_fields = ('name', 'key', 'description')

class EvaluationAssignmentAdmin(admin.ModelAdmin):
    list_display = ('evaluator', 'date_assigned', 'is_completed')
    list_filter = ('is_completed', 'date_assigned')
    autocomplete_fields = ['form_submission', 'evaluator']
    search_fields = [
        'form_submission__form_id',
        'form_submission__subject',
        'evaluator__email',
        'evaluator__full_name',
    ]

    def get_subject(self, obj):
        subject = getattr(obj.form_submission, 'subject', None)
        if not subject:
            subject = getattr(obj.form_submission, 'title', f"Form {obj.form_submission.form_id}")
        return subject
    get_subject.short_description = 'Subject'

class CriteriaEvaluationAdmin(admin.ModelAdmin):
    list_display = ('get_assignment', 'get_criteria', 'marks_given', 'date_evaluated')
    search_fields = ('assignment__form_submission__form_id', 'criteria__name')
    autocomplete_fields = ['assignment', 'criteria']  # Change to autocomplete
    
    def get_assignment(self, obj):
        subject = getattr(obj.assignment.form_submission, 'subject', 
                  getattr(obj.assignment.form_submission, 'title', 
                  f"Form {obj.assignment.form_submission.form_id}"))
        return f"{obj.assignment.evaluator} - {subject}"
    get_assignment.short_description = 'Assignment'
    
    def get_criteria(self, obj):
        return obj.criteria.name
    get_criteria.short_description = 'Criteria'

class QuestionEvaluationAdmin(admin.ModelAdmin):
    list_display = ('get_assignment', 'get_question', 'marks_given', 'date_evaluated')
    search_fields = ('assignment__form_submission__form_id', 'question__name')
    autocomplete_fields = ['assignment', 'question']  # Change to autocomplete
    
    def get_assignment(self, obj):
        subject = getattr(obj.assignment.form_submission, 'subject', 
                  getattr(obj.assignment.form_submission, 'title', 
                  f"Form {obj.assignment.form_submission.form_id}"))
        return f"{obj.assignment.evaluator} - {subject}"
    get_assignment.short_description = 'Assignment'
    
    def get_question(self, obj):
        return obj.question.name
    get_question.short_description = 'Question'

class EvaluationCutoffAdmin(admin.ModelAdmin):
    list_display = ('get_service_name', 'cutoff_marks', 'created_by', 'date_created')
    search_fields = ('service__name',)   
    autocomplete_fields = ['service']   

    def get_service_name(self, obj):
        return obj.service.name if obj.service else None
    get_service_name.short_description = 'Service'



admin.site.register(CriteriaType, CriteriaTypeAdmin)
admin.site.register(Evaluator, EvaluatorAdmin)
admin.site.register(EvaluationItem, EvaluationItemAdmin)
admin.site.register(EvaluationAssignment, EvaluationAssignmentAdmin)
admin.site.register(CriteriaEvaluation, CriteriaEvaluationAdmin)
admin.site.register(QuestionEvaluation, QuestionEvaluationAdmin)
admin.site.register(EvaluationCutoff, EvaluationCutoffAdmin)
