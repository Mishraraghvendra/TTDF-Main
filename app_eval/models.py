# app_eval/models.py

from django.db import models
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from dynamic_form.models import FormSubmission
# from configuration.models import Service

STATUS_CHOICES = [
    ('Active', 'Active'),
    ('Inactive', 'Inactive'),
]

class PassingRequirement(models.Model):
    # service = models.ForeignKey(Service,on_delete=models.CASCADE,related_name='passing_requirements')

    requirement_name = models.CharField(max_length=255)
    evaluation_min_passing = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    presentation_min_passing = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    presentation_max_marks = models.PositiveIntegerField(default=0)
    final_status_min_passing = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')

    # def __str__(self):
    #     return f"{self.requirement_name}  ({self.service.name})"
    def __str__(self):
        return self.requirement_name



class CriteriaType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Evaluator(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.email
    
# class AssignEvaluators(models.Model):
#     form_submission = models.ForeignKey(FormSubmission,on_delete=models.CASCADE,related_name='assign_evaluators')
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     department = models.CharField(max_length=100, blank=True, null=True)

#     def __str__(self):
#         return self.user.get_full_name() or self.user.email    

class EvaluationItem(models.Model):  
    TYPE_CHOICES = [
        ('criteria', 'Criteria'),
        ('question', 'Question')
    ]

    name = models.CharField(max_length=100)
    key = models.CharField(max_length=50, unique=True, null=True, blank=True)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=[('Active','Active'),('Inactive','Inactive')], default='Active')
    description = models.TextField(blank=True, null=True)
    memberType = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.type})"


class EvaluationAssignment(models.Model):
    form_submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name='eval_assignments')
    evaluator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    current_trl = models.IntegerField(blank=True, null=True)  # auto-populated from form_submission
    expected_trl = models.IntegerField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    conflict_of_interest = models.BooleanField(default=False)
    conflict_remarks = models.TextField(blank=True, null=True)
    total_marks_assigned = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    evaluated_at = models.DateTimeField(blank=True, null=True)

    date_assigned = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('form_submission', 'evaluator')

    def __str__(self):
        return f"{self.evaluator} assigned to {self.form_submission}"
    

class CriteriaEvaluation(models.Model):
    assignment = models.ForeignKey(EvaluationAssignment, on_delete=models.CASCADE, related_name='criteria_evaluations')
    criteria = models.ForeignKey(EvaluationItem, on_delete=models.CASCADE, related_name='criteria_evaluations')
    marks_given = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    comments = models.TextField(blank=True, null=True)
    date_evaluated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('assignment', 'criteria')

    def __str__(self):
        return f"Evaluation of {self.criteria.name} by {self.assignment.evaluator}"

class QuestionEvaluation(models.Model):
    assignment = models.ForeignKey(EvaluationAssignment, on_delete=models.CASCADE, related_name='question_evaluations')
    question = models.ForeignKey(EvaluationItem, on_delete=models.CASCADE, related_name='question_evaluations')
    marks_given = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    comments = models.TextField(blank=True, null=True)
    date_evaluated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('assignment', 'question')

    def __str__(self):
        return f"Evaluation of question by {self.assignment.evaluator}"

class EvaluationCutoff(models.Model):
    # Direct link to FormSubmission instead of Proposal
    form_submission = models.OneToOneField(
        FormSubmission, 
        on_delete=models.CASCADE, 
        related_name='eval_cutoff'
    )
    cutoff_marks = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Get subject from form_submission if available
        subject = getattr(self.form_submission, 'subject', None)
        if not subject:
            # Try to get it from another field or use ID
            subject = getattr(self.form_submission, 'title', f"Form {self.form_submission.form_id}")
        return f"Cutoff for {subject}: {self.cutoff_marks}"

