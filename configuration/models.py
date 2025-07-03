# configuration/models.py
from django.db import models
from django.conf import settings
import uuid
from dynamic_form.models import FormSubmission
from django.utils import timezone


class ConfigurationProfile(models.Model):
    
    id         = models.UUIDField(
                    primary_key=True,
                    default=uuid.uuid4,
                    editable=False
                 )
    user       = models.OneToOneField(
                    settings.AUTH_USER_MODEL,
                    on_delete=models.CASCADE,
                    related_name='configuration_profile'
                 )
    role       = models.CharField(
                    max_length=20,
                    choices=(
                        ('superadmin', 'Super Admin'),
                        ('admin',      'Admin'),
                        ('evaluator',  'Evaluator'),
                        ('applicant',  'Applicant'),
                    ),
                    default='applicant'
                 )
    department = models.CharField(max_length=100, blank=True, null=True)
    phone      = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Config for {self.user.get_full_name() or self.user.email}"


# class Service(models.Model):
   
#     STATUS_CHOICES = (
#         ('draft', 'Draft'),
#         ('active', 'Active'),
#         ('stopped', 'Stopped'),
#     )    
#     name        = models.CharField(max_length=255)
#     description = models.TextField(blank=True, null=True)
#     is_active   = models.BooleanField(default=True)  # You can keep for legacy or remove
#     start_date = models.DateTimeField(null=True, blank=True)
#     end_date   = models.DateTimeField(null=True, blank=True)
#     status      = models.CharField(
#                     max_length=20,
#                     choices=STATUS_CHOICES,
#                     default='draft',
#                     help_text="Draft: not visible to applicants, Active: open for applications."
#                  )
#     created_by  = models.ForeignKey(
#                     settings.AUTH_USER_MODEL,
#                     on_delete=models.SET_NULL,
#                     null=True,
#                     related_name='created_services'
#                  )
#     created_at  = models.DateTimeField(auto_now_add=True)
#     updated_at  = models.DateTimeField(auto_now=True)

#     @property
#     def is_currently_active(self):
#         if not self.is_active:
#             return False
#         if self.end_date and timezone.now() > self.end_date:
#             return False
#         return True

#     def __str__(self):
#         return self.name


def service_document_upload_path(instance, filename):
    # Customize as needed
    return f"services/{instance.id}/documents/{filename}"

def service_image_upload_path(instance, filename):
    return f"services/{instance.id}/images/{filename}"

class Service(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('stopped', 'Stopped'),
    )    
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active   = models.BooleanField(default=True)
    start_date  = models.DateTimeField(null=True, blank=True)
    end_date    = models.DateTimeField(null=True, blank=True)
    schedule_date = models.DateTimeField(null=True, blank=True)  # New field

    image      = models.ImageField(
        upload_to=service_image_upload_path, null=True, blank=True
    )  # New field

    documents  = models.FileField(
        upload_to=service_document_upload_path, null=True, blank=True
    )  # For one document. For multiple, see note below

    status      = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Draft: not visible to applicants, Active: open for applications."
    )
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_services'
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    @property
    def is_currently_active(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

    def save(self, *args, **kwargs):
        now = timezone.now()
        # Automatically set is_active based on dates
        if self.start_date and now < self.start_date:
            self.is_active = False
        elif self.end_date and now > self.end_date:
            self.is_active = False
        else:
            self.is_active = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ServiceForm(models.Model):
    """
    Links a Service to a dynamic form template (in dynamic_form app).
    """
    id          = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    service     = models.ForeignKey(Service,on_delete=models.CASCADE,related_name='forms')
    # Uncomment and adjust when dynamic_form is available
    # form_template = models.ForeignKey(
    #                 'dynamic_form.FormTemplate',
    #                 on_delete=models.CASCADE,
    #                 related_name='services'
    #              )
    is_active   = models.BooleanField(default=True)
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name='created_service_forms')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Form for {self.service.name}"


class ScreeningCommittee(models.Model):
    """
    Committees that perform administrative or technical screening.
    """
    COMMITTEE_TYPES = (
        ('administrative', 'Administrative Screening'),
        ('technical',     'Technical Screening'),
    )

    id             = models.UUIDField(
                       primary_key=True,
                       default=uuid.uuid4,
                       editable=False
                    )
    service        = models.ForeignKey(
                       Service,
                       on_delete=models.CASCADE,
                       related_name='screening_committees'
                    )
    name           = models.CharField(max_length=255)
    committee_type = models.CharField(max_length=20, choices=COMMITTEE_TYPES)
    description    = models.TextField(blank=True, null=True)
    head           = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL,
                       null=True,
                       related_name='headed_committees'
                    )
    sub_head       = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL,
                       null=True,
                       related_name='sub_headed_committees'
                    )
    is_active      = models.BooleanField(default=True)
    created_by     = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL,
                       null=True,
                       related_name='created_committees'
                    )
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('service', 'committee_type')

    def __str__(self):
        return f"{self.service.name} - {self.get_committee_type_display()}"


class CommitteeMember(models.Model):
    """
    Members (users) assigned to a screening committee.
    """
    id          = models.UUIDField(
                       primary_key=True,
                       default=uuid.uuid4,
                       editable=False
                    )
    committee   = models.ForeignKey(
                       ScreeningCommittee,
                       on_delete=models.CASCADE,
                       related_name='members'
                    )
    user        = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.CASCADE,
                       related_name='committee_memberships'
                    )
    is_active   = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL,
                       null=True,
                       related_name='assigned_members'
                    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('committee', 'user')

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} in {self.committee.name}"


class ScreeningResult(models.Model):
    """
    Result of a screening round for a given application.
    """
    RESULT_CHOICES = (
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ) 

    id          = models.UUIDField(
                       primary_key=True,
                       default=uuid.uuid4,
                       editable=False
                    )
    application = models.ForeignKey(FormSubmission,
        to_field='proposal_id',
        on_delete=models.CASCADE,
                       related_name='screening_results'
                    )
    committee   = models.ForeignKey(
                       ScreeningCommittee,
                       on_delete=models.CASCADE,
                       related_name='screenings'
                    )
    result      = models.CharField(max_length=20, choices=RESULT_CHOICES, default='pending')
    notes       = models.TextField(blank=True, null=True)
    screened_by = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL,
                       null=True,
                       related_name='screenings'
                    )
    screened_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('application', 'committee')

    def __str__(self):
        return f"{self.application} - {self.committee.get_committee_type_display()}: {self.result}"


class EvaluationStage(models.Model):
    """
    Defines each evaluation stage (beyond screening) for a service.
    """
    id           = models.UUIDField(
                       primary_key=True,
                       default=uuid.uuid4,
                       editable=False
                    )
    service      = models.ForeignKey(
                       Service,
                       on_delete=models.CASCADE,
                       related_name='evaluation_stages'
                    )
    name         = models.CharField(max_length=100)
    description  = models.TextField(blank=True, null=True)
    order        = models.PositiveIntegerField(default=1)
    is_active    = models.BooleanField(default=True)
    cutoff_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_by   = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL,
                       null=True
                    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ('service', 'order')

    def __str__(self):
        return f"{self.service.name} - {self.name} (Stage {self.order})"


class EvaluationCriteriaConfig(models.Model):
    """
    Maps form fields to evaluative criteria for scoring.
    """
    id             = models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False
                     )
    stage          = models.ForeignKey(
                        EvaluationStage,
                        on_delete=models.CASCADE,
                        related_name='criteria_configs'
                     )
    name           = models.CharField(max_length=255, default="Custom Criteria")

    # field          = models.ForeignKey(
    #                     'dynamic_form.FormField',
    #                     on_delete=models.CASCADE,
    #                     related_name='evaluation_configs',null=True, blank=True)
    
    criteria_type  = models.ForeignKey(
                        'app_eval.CriteriaType',
                        on_delete=models.CASCADE,
                        null=True,
                        blank=True
                     )
    total_marks    = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    weight         = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
                                     
    created_by     = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL,
                        null=True
                     )
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.stage.name} - {self.field.label} ({self.total_marks} marks)"


class EvaluatorAssignment(models.Model):
    """
    Assigns evaluators to specific evaluation stages.
    """
    id           = models.UUIDField(
                       primary_key=True,
                       default=uuid.uuid4,
                       editable=False
                    )
    user         = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.CASCADE,
                       related_name='evaluator_assignments'
                    )
    stage        = models.ForeignKey(
                       EvaluationStage,
                       on_delete=models.CASCADE,
                       related_name='evaluators'
                    )
    assigned_by  = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL,
                       null=True,
                       related_name='assigned_evaluators'
                    )
    assigned_at  = models.DateTimeField(auto_now_add=True)
    is_active    = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'stage')

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} assigned to {self.stage.name}"


class Application(models.Model):
    """
    Represents an application submitted by a user for a service.
    """
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('administrative_screening', 'Administrative Screening'),
        ('technical_screening', 'Technical Screening'),
        ('under_evaluation', 'Under Evaluation'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    id            = models.UUIDField(
                       primary_key=True,
                       default=uuid.uuid4,
                       editable=False
                    )
    service       = models.ForeignKey(
                       Service,
                       on_delete=models.CASCADE,
                       related_name='applications'
                    )
    applicant     = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.CASCADE,
                       related_name='applications'
                    )
    # form_submission = models.ForeignKey(
    #                    'dynamic_form.FormSubmission',
    #                    on_delete=models.CASCADE,
    #                    related_name='applications',
    #                    null=True,
    #                    blank=True
    #                 )
    status        = models.CharField(max_length=25, choices=STATUS_CHOICES, default='draft')
    submitted_at  = models.DateTimeField(null=True, blank=True)
    current_stage = models.ForeignKey(
                       EvaluationStage,
                       on_delete=models.SET_NULL,
                       null=True,
                       blank=True,
                       related_name='current_applications'
                    )

    def __str__(self):
        return f"{self.applicant.get_full_name() or self.applicant.email} - {self.service.name}"


class ApplicationStageProgress(models.Model):
    """
    Tracks progress for each stage of an application.
    """
    STAGE_STATUS = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    )

    id              = models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False
                     )
    application     = models.ForeignKey(
                        Application,
                        on_delete=models.CASCADE,
                        related_name='stage_progress'
                     )
    stage           = models.ForeignKey(
                        EvaluationStage,
                        on_delete=models.CASCADE,
                        related_name='application_progress'
                     )
    status          = models.CharField(max_length=20, choices=STAGE_STATUS, default='pending')
    start_date      = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    total_score     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('application', 'stage')

    def __str__(self):
        return f"{self.application} - {self.stage.name}: {self.status}"


class CriteriaEvaluatorAssignment(models.Model):
    """
    Assigns evaluators to specific criteria configurations.
    """
    id           = models.UUIDField(
                       primary_key=True,
                       default=uuid.uuid4,
                       editable=False
                    )
    criteria     = models.ForeignKey(
                       EvaluationCriteriaConfig,
                       on_delete=models.CASCADE,
                       related_name='evaluator_assignments'
                    )
    evaluator    = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.CASCADE,
                       related_name='criteria_assignments'
                    )
    assigned_by  = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL,
                       null=True,
                       related_name='assigned_criteria_evaluators'
                    )
    assigned_at  = models.DateTimeField(auto_now_add=True)
    is_active    = models.BooleanField(default=True)

    class Meta:
        unique_together = ('criteria', 'evaluator')

    def __str__(self):
        return f"{self.evaluator.get_full_name() or self.evaluator.username} assigned to {self.criteria.name}"