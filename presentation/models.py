# presentation/models.py
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from dynamic_form.models import FormSubmission

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


DECISION_CHOICES = (
    ('pending', 'Pending'),
    ('assigned', 'Assigned'),  # Added for when admin assigns video/doc/date
    ('evaluated', 'Evaluated'),  # Added for when evaluator submits marks
    ('shortlisted', 'Shortlisted'),
    ('rejected', 'Rejected'),
) 

# class Presentation(models.Model):
#     # Core fields
#     proposal = models.ForeignKey(
#         FormSubmission,
#         to_field='proposal_id',
#         on_delete=models.CASCADE,
#         related_name='presentations'
#     )
#     applicant = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name='presentations'
#     )
#     video_link = models.URLField(
#     max_length=500,
#     null=True,
#     blank=True,
#     help_text="Optional video link instead of uploaded file"
# )

#     # Media files - uploaded by admin
#     video = models.FileField(
#         upload_to="presentation/videos/",         null=True,         blank=True,        help_text="Video file uploaded by admin"    )
#     document = models.FileField(        upload_to="presentation/documents/",         null=True,         blank=True,        help_text="Presentation document uploaded by admin"
#     )
#     presentation_date = models.DateTimeField(        null=True,        blank=True,        help_text="Scheduled date and time for the presentation"
#     )
    
#     # Status tracking
#     document_uploaded = models.BooleanField(        default=False,        help_text="True once video + document + date are all provided by admin"
#     )
    
#     # Timestamps
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     # Evaluation by evaluator (same as tech evaluation)
#     evaluator = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='presentation_evaluations',        help_text="Evaluator assigned from technical evaluation"
#     )
#     evaluator_marks = models.DecimalField(
#         max_digits=5, 
#         decimal_places=2, 
#         null=True, 
#         blank=True,
#         help_text="Marks given by evaluator (out of max presentation marks)"
#     )
#     evaluator_remarks = models.TextField(
#         blank=True, 
#         null=True,
#         help_text="Evaluator's remarks and feedback"
#     )
#     evaluated_at = models.DateTimeField(
#         null=True, 
#         blank=True,
#         help_text="When evaluator submitted the evaluation"
#     )

#     # Final decision by admin
#     final_decision = models.CharField(
#         max_length=20, 
#         choices=DECISION_CHOICES, 
#         default='pending'
#     )
#     admin_remarks = models.TextField(
#         blank=True, 
#         null=True,
#         help_text="Admin's final remarks"
#     )
#     admin = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='presentation_admin_decisions'
#     )
#     admin_evaluated_at = models.DateTimeField(
#         null=True, 
#         blank=True,
#         help_text="When admin made final decision"
#     )

#     class Meta:
#         ordering = ['-created_at']
#         unique_together = ['proposal', 'applicant','evaluator']  # One presentation per proposal

#     def __str__(self):
#         return f"Presentation {self.proposal.proposal_id} by {self.applicant.get_full_name()}"

#     @property
#     def is_ready_for_evaluation(self):
#         """Check if presentation is ready for evaluator to give marks"""
#         return (
#             self.document_uploaded and 
#             self.evaluator and 
#             self.final_decision == 'assigned'
#         )

#     @property
#     def is_evaluation_completed(self):
#         """Check if evaluator has completed evaluation"""
#         return (
#             self.evaluator_marks is not None and 
#             self.evaluated_at is not None
#         )

#     @property
#     def can_make_final_decision(self):
#         """Check if admin can make final decision"""
#         return (
#             self.is_evaluation_completed and
#             self.final_decision in ['evaluated']
#         )

#     def update_evaluator_info(self, evaluator_user):
#         """Update evaluator assignment"""
#         self.evaluator = evaluator_user
#         self.save(update_fields=['evaluator'])

#     def submit_evaluation(self, marks, remarks):
#         """Submit evaluator marks and remarks"""
#         self.evaluator_marks = marks
#         self.evaluator_remarks = remarks
#         self.evaluated_at = timezone.now()
#         self.final_decision = 'evaluated'
#         self.save(update_fields=[
#             'evaluator_marks', 
#             'evaluator_remarks', 
#             'evaluated_at', 
#             'final_decision'
#         ])

#     def update_admin_decision(self, admin_user, decision, remarks=None):
#         """Update final admin decision"""
#         self.final_decision = decision
#         self.admin_remarks = remarks
#         self.admin = admin_user
#         self.admin_evaluated_at = timezone.now()
#         self.save(update_fields=[
#             'final_decision', 
#             'admin_remarks', 
#             'admin', 
#             'admin_evaluated_at'
#         ])

#     def assign_materials(self, video_file=None, video_link=None, document_file=None, presentation_date=None, admin_user=None):
#         """Admin assigns presentation materials"""
#         if video_link:
#            self.video_link = video_link
#         if video_file:
#            self.video = video_file
#         if document_file:
#            self.document = document_file
#         if presentation_date:
#            self.presentation_date = presentation_date
    
#         if admin_user:
#            self.admin = admin_user
#            self.admin_evaluated_at = timezone.now()
    
#     # Check if all materials are now complete
#         has_video = bool(self.video or self.video_link)
#         has_document = bool(self.document)
#         has_date = bool(self.presentation_date)
    
#         if has_video and has_document and has_date:
#            self.document_uploaded = True
#            if self.final_decision == 'pending':
#              self.final_decision = 'assigned'
    
#         self.save()

#     def save(self, *args, **kwargs):
#         """Auto-update document_uploaded status and final_decision"""
#     # Check if all required materials are present
#         has_video = bool(self.video or self.video_link)
#         has_document = bool(self.document)
#         has_date = bool(self.presentation_date)
    
#         if has_video and has_document and has_date:
#            self.document_uploaded = True
#         # Auto-assign status if still pending
#            if self.final_decision == 'pending':
#             self.final_decision = 'assigned'
#         else:
#            self.document_uploaded = False
#         # Keep as pending if materials are incomplete
#            if self.final_decision == 'assigned' and not (has_video and has_document and has_date):
#             self.final_decision = 'pending'
    
#         super().save(*args, **kwargs)



class PresentationCache(models.Model):
    form_submission = models.OneToOneField(
        'dynamic_form.FormSubmission',
        on_delete=models.CASCADE,
        related_name='presentation_cache'
    )
    cached_summary = models.JSONField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return f"PresentationCache for {self.form_submission.proposal_id}"




class Presentation(models.Model):
    proposal = models.ForeignKey(
        'dynamic_form.FormSubmission',
        to_field='proposal_id',
        on_delete=models.CASCADE,
        related_name='presentations'
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='presentations'
    )
    video_link = models.URLField(max_length=500, null=True, blank=True)
    video = models.FileField(upload_to="presentation/videos/", null=True, blank=True)
    document = models.FileField(upload_to="presentation/documents/", null=True, blank=True)
    presentation_date = models.DateTimeField(null=True, blank=True)
    document_uploaded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='presentation_evaluations'
    )
    evaluator_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    evaluator_remarks = models.TextField(blank=True, null=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    final_decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default='pending')
    admin_remarks = models.TextField(blank=True, null=True)
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='presentation_admin_decisions'
    )
    admin_evaluated_at = models.DateTimeField(null=True, blank=True)

    # Cache fields
    cached_status = models.CharField(max_length=100, blank=True, null=True)
    cached_evaluator_name = models.CharField(max_length=200, blank=True, null=True)
    cached_marks_summary = models.JSONField(blank=True, null=True)
    cached_applicant_data = models.JSONField(blank=True, null=True)
    cache_updated_at = models.DateTimeField(auto_now=True)
    cached_admin_name = models.CharField(max_length=200, blank=True, null=True)
    cached_final_decision_display = models.CharField(max_length=100, blank=True, null=True)
    cached_video_url = models.TextField(blank=True, null=True)
    cached_document_url = models.TextField(blank=True, null=True)
    cached_is_ready_for_evaluation = models.BooleanField(default=False)
    cached_is_evaluation_completed = models.BooleanField(default=False)
    cached_can_make_final_decision = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['proposal', 'applicant', 'evaluator']
        indexes = [models.Index(fields=["cached_status", "-created_at"])]

    def __str__(self):
        return f"Presentation {self.proposal.proposal_id} by {self.applicant.get_full_name()}"

    @property
    def is_ready_for_evaluation(self):
        return self.document_uploaded and self.evaluator and self.final_decision == 'assigned'

    @property
    def is_evaluation_completed(self):
        return self.evaluator_marks is not None and self.evaluated_at is not None

    @property
    def can_make_final_decision(self):
        return self.is_evaluation_completed and self.final_decision == 'evaluated'

    def assign_materials(self, video_file=None, video_link=None, document_file=None, presentation_date=None, admin_user=None):
        """
        Assign presentation materials and update document_uploaded flag.
        """
        if video_link is not None:
            self.video_link = video_link
        if video_file is not None:
            self.video = video_file
        if document_file is not None:
            self.document = document_file
        if presentation_date is not None:
            self.presentation_date = presentation_date
        if admin_user is not None:
            self.admin = admin_user
            self.admin_evaluated_at = timezone.now()

        # Determine if all required materials are present
        has_video = bool(self.video or self.video_link)
        has_document = bool(self.document)
        has_date = bool(self.presentation_date)

        if has_video and has_document and has_date:
            self.document_uploaded = True
            if self.final_decision == 'pending':
                self.final_decision = 'assigned'
        else:
            self.document_uploaded = False
            if self.final_decision == 'assigned':
                self.final_decision = 'pending'
        self.save()

 
    def submit_evaluation(self, evaluator_marks, evaluator_remarks, evaluator_user=None):
        """
        Submit evaluation marks and remarks for the presentation.
        """
        if evaluator_user is None:
            evaluator_user = self.evaluator  # fallback
        
        self.evaluator_marks = evaluator_marks
        self.evaluator_remarks = evaluator_remarks
        self.evaluator = evaluator_user
        self.evaluated_at = timezone.now()
        self.final_decision = 'evaluated'
        self.update_cached_values()
        self.save()

    def update_cached_values(self, save=True):
            self.cached_evaluator_name = self.evaluator.get_full_name() if self.evaluator else None
            self.cached_status = self.final_decision
            self.cached_marks_summary = {
                "marks": float(self.evaluator_marks) if self.evaluator_marks is not None else None,
                "remarks": self.evaluator_remarks,
                "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            }
            self.cached_admin_name = self.admin.get_full_name() if self.admin else None
            self.cached_final_decision_display = self.get_final_decision_display() if self.final_decision else ""
            self.cached_video_url = self.video.url if self.video else ""
            self.cached_document_url = self.document.url if self.document else ""
            self.cached_is_ready_for_evaluation = self.is_ready_for_evaluation
            self.cached_is_evaluation_completed = self.is_evaluation_completed
            self.cached_can_make_final_decision = self.can_make_final_decision

            if self.applicant:
                self.cached_applicant_data = {
                    "id": self.applicant.id,
                    "name": self.applicant.get_full_name() if hasattr(self.applicant, "get_full_name") else str(self.applicant),
                    "email": getattr(self.applicant, "email", None),
                    "organization": getattr(self.applicant, "organization", None),
                }
            else:
                self.cached_applicant_data = {}

            self.cache_updated_at = timezone.now()
            
            if save:
                self._disable_signal = True
                self.save(update_fields=[
                    "cached_status", "cached_evaluator_name", "cached_admin_name",
                    "cached_final_decision_display", "cached_video_url", "cached_document_url",
                    "cached_is_ready_for_evaluation", "cached_is_evaluation_completed",
                    "cached_can_make_final_decision", "cached_marks_summary", "cached_applicant_data",
                    "cache_updated_at"
                ])
                del self._disable_signal

    def update_admin_decision(self, decision, remarks=None, admin_user=None, save=True):
        """
        Update the final_decision and optionally admin remarks/admin user.
        """
        self.final_decision = decision
        if remarks is not None:
            self.admin_remarks = remarks
        if admin_user is not None:
            self.admin = admin_user
            self.admin_evaluated_at = timezone.now()
        self.update_cached_values(save=False)
        if save:
            self.save(update_fields=[
                "final_decision",
                "admin_remarks",
                "admin",
                "admin_evaluated_at",
                "cached_status",
                "cached_admin_name",
                "cached_final_decision_display",
                "cache_updated_at",
            ])

# ✅ Helper to update proposal cache
def update_proposal_presentation_cache(form_submission):
    presentations = form_submission.presentations.all().select_related('evaluator', 'admin', 'applicant')
    presentation_list = []
    total_marks = 0
    evaluated_count = 0

    for p in presentations:
        marks = float(p.evaluator_marks) if p.evaluator_marks is not None else None
        presentation_list.append({
            "id": p.id,
            "evaluator_id": p.evaluator.id if p.evaluator else None,
            "evaluator_name": p.cached_evaluator_name,
            "evaluator_email": (p.cached_applicant_data or {}).get('email'),
            "marks": marks,
            "remarks": p.evaluator_remarks,
            "evaluated_at": p.evaluated_at.isoformat() if p.evaluated_at else None,
            "is_completed": p.is_evaluation_completed,
            "video_url": p.cached_video_url,
            "document_url": p.cached_document_url,
            "final_decision": p.final_decision,
        })
        if marks is not None:
            total_marks += marks
            evaluated_count += 1

    average_marks = round(total_marks / evaluated_count, 2) if evaluated_count else 0
    summary = {
        "presentations": presentation_list,
        "total_evaluators": len(presentation_list),
        "evaluated_count": evaluated_count,
        "average_marks": average_marks,
        "last_updated": timezone.now().isoformat()
    }

    # Optional if you don't store on FormSubmission
    # form_submission.presentation_cached_summary = summary
    # form_submission.presentation_cache_updated_at = timezone.now()
    # form_submission.save(update_fields=['presentation_cached_summary', 'presentation_cache_updated_at'])

    # If you only want to return this (Option 1), do not save it
    return summary


# ✅ Split signal receivers

@receiver(post_save, sender=Presentation)
def auto_update_presentation_cache_on_save(sender, instance, **kwargs):
    if getattr(instance, "_disable_signal", False):
        return
    instance.update_cached_values()
    if instance.proposal_id:
        update_proposal_presentation_cache(instance.proposal)


@receiver(post_delete, sender=Presentation)
def auto_update_presentation_cache_on_delete(sender, instance, **kwargs):
    if instance.proposal_id:
        update_proposal_presentation_cache(instance.proposal)





# class Presentation(models.Model):
#     proposal = models.ForeignKey(
#         'dynamic_form.FormSubmission',
#         to_field='proposal_id',
#         on_delete=models.CASCADE,
#         related_name='presentations'
#     )
#     applicant = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name='presentations'
#     )
#     video_link = models.URLField(max_length=500, null=True, blank=True)
#     video = models.FileField(upload_to="presentation/videos/", null=True, blank=True)
#     document = models.FileField(upload_to="presentation/documents/", null=True, blank=True)
#     presentation_date = models.DateTimeField(null=True, blank=True)
#     document_uploaded = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     evaluator = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True, blank=True,
#         related_name='presentation_evaluations'
#     )
#     evaluator_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
#     evaluator_remarks = models.TextField(blank=True, null=True)
#     evaluated_at = models.DateTimeField(null=True, blank=True)
#     final_decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default='pending')
#     admin_remarks = models.TextField(blank=True, null=True)
#     admin = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True, blank=True,
#         related_name='presentation_admin_decisions'
#     )
#     admin_evaluated_at = models.DateTimeField(null=True, blank=True)
#     # Cache fields
#     cached_status = models.CharField(max_length=100, blank=True, null=True)
#     cached_evaluator_name = models.CharField(max_length=200, blank=True, null=True)
#     cached_marks_summary = models.JSONField(blank=True, null=True)
#     cached_applicant_data = models.JSONField(blank=True, null=True)
#     cache_updated_at = models.DateTimeField(auto_now=True) 
#     cached_admin_name = models.CharField(max_length=200, blank=True, null=True)
#     cached_final_decision_display = models.CharField(max_length=100, blank=True, null=True)
#     cached_video_url = models.TextField(blank=True, null=True)
#     cached_document_url = models.TextField(blank=True, null=True)
#     cached_is_ready_for_evaluation = models.BooleanField(default=False)
#     cached_is_evaluation_completed = models.BooleanField(default=False)
#     cached_can_make_final_decision = models.BooleanField(default=False)

#     class Meta:
#         ordering = ['-created_at']
#         unique_together = ['proposal', 'applicant', 'evaluator']
#         indexes = [models.Index(fields=["cached_status", "-created_at"])]

#     def __str__(self):
#         return f"Presentation {self.proposal.proposal_id} by {self.applicant.get_full_name()}"

#     @property
#     def is_ready_for_evaluation(self):
#         return self.document_uploaded and self.evaluator and self.final_decision == 'assigned'

#     @property
#     def is_evaluation_completed(self):
#         return self.evaluator_marks is not None and self.evaluated_at is not None

#     @property
#     def can_make_final_decision(self):
#         return self.is_evaluation_completed and self.final_decision == 'evaluated'
    

#     def assign_materials(self, video_file=None, video_link=None, document_file=None, presentation_date=None, admin_user=None):
#             """
#             Assign presentation materials and update document_uploaded flag.
#             """
#             if video_link is not None:
#                 self.video_link = video_link
#             if video_file is not None:
#                 self.video = video_file
#             if document_file is not None:
#                 self.document = document_file
#             if presentation_date is not None:
#                 self.presentation_date = presentation_date
#             if admin_user is not None:
#                 self.admin = admin_user
#                 self.admin_evaluated_at = timezone.now()

#             # Determine if all required materials are present
#             has_video = bool(self.video or self.video_link)
#             has_document = bool(self.document)
#             has_date = bool(self.presentation_date)

#             if has_video and has_document and has_date:
#                 self.document_uploaded = True
#                 if self.final_decision == 'pending':
#                     self.final_decision = 'assigned'
#             else:
#                 self.document_uploaded = False
#                 if self.final_decision == 'assigned':
#                     self.final_decision = 'pending'
#             self.save()



#     def update_cached_values(self, save=True):
#         self.cached_evaluator_name = self.evaluator.get_full_name() if self.evaluator else None
#         self.cached_status = self.final_decision
#         self.cached_marks_summary = {
#             "marks": float(self.evaluator_marks) if self.evaluator_marks is not None else None,
#             "remarks": self.evaluator_remarks,
#             "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
#         }
#         self.cached_admin_name = self.admin.get_full_name() if self.admin else None
#         self.cached_final_decision_display = self.get_final_decision_display() if self.final_decision else ""
#         self.cached_video_url = self.video.url if self.video else ""
#         self.cached_document_url = self.document.url if self.document else ""
#         self.cached_is_ready_for_evaluation = self.is_ready_for_evaluation
#         self.cached_is_evaluation_completed = self.is_evaluation_completed
#         self.cached_can_make_final_decision = self.can_make_final_decision

#         if self.applicant:
#             self.cached_applicant_data = {
#                 "id": self.applicant.id,
#                 "name": self.applicant.get_full_name() if hasattr(self.applicant, "get_full_name") else str(self.applicant),
#                 "email": getattr(self.applicant, "email", None),
#                 "organization": getattr(self.applicant, "organization", None),
#             }
#         else:
#             self.cached_applicant_data = {}

#         self.cache_updated_at = timezone.now()
#         if save:
#             self._disable_signal = True
#             self.save(update_fields=[
#                 "cached_status", "cached_evaluator_name", "cached_admin_name",
#                 "cached_final_decision_display", "cached_video_url", "cached_document_url",
#                 "cached_is_ready_for_evaluation", "cached_is_evaluation_completed",
#                 "cached_can_make_final_decision",
#                 "cached_marks_summary", "cached_applicant_data", "cache_updated_at"
#             ])
#             del self._disable_signal


# @receiver([post_save, post_delete], sender=Presentation)
# def auto_update_presentation_cache(sender, instance, **kwargs):
#     if getattr(instance, "_disable_signal", False):
#         return
#     instance.update_cached_values()





# class Presentation(models.Model):
    
#     proposal = models.ForeignKey(
#         'dynamic_form.FormSubmission',
#         to_field='proposal_id',
#         on_delete=models.CASCADE,
#         related_name='presentations'
#     )
#     applicant = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name='presentations'
#     )
#     video_link = models.URLField(
#         max_length=500, null=True, blank=True,
#         help_text="Optional video link instead of uploaded file"
#     )
#     video = models.FileField(
#         upload_to="presentation/videos/", null=True, blank=True,
#         help_text="Video file uploaded by admin"
#     )
#     document = models.FileField(
#         upload_to="presentation/documents/", null=True, blank=True,
#         help_text="Presentation document uploaded by admin"
#     )
#     presentation_date = models.DateTimeField(
#         null=True, blank=True,
#         help_text="Scheduled date and time for the presentation"
#     )
#     document_uploaded = models.BooleanField(
#         default=False,
#         help_text="True once video + document + date are all provided by admin"
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     evaluator = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True, blank=True,
#         related_name='presentation_evaluations',
#         help_text="Evaluator assigned from technical evaluation"
#     )
#     evaluator_marks = models.DecimalField(
#         max_digits=5, decimal_places=2, null=True, blank=True,
#         help_text="Marks given by evaluator (out of max presentation marks)"
#     )
#     evaluator_remarks = models.TextField(
#         blank=True, null=True,
#         help_text="Evaluator's remarks and feedback"
#     )
#     evaluated_at = models.DateTimeField(
#         null=True, blank=True,
#         help_text="When evaluator submitted the evaluation"
#     )
#     final_decision = models.CharField(
#         max_length=20, choices=DECISION_CHOICES, default='pending'
#     )
#     admin_remarks = models.TextField(
#         blank=True, null=True,
#         help_text="Admin's final remarks"
#     )
#     admin = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True, blank=True,
#         related_name='presentation_admin_decisions'
#     )
#     admin_evaluated_at = models.DateTimeField(
#         null=True, blank=True,
#         help_text="When admin made final decision"
#     )

#     # --- Caching fields (NEW) ---
#     cached_status = models.CharField(max_length=100, blank=True, null=True)
#     cached_evaluator_name = models.CharField(max_length=200, blank=True, null=True)
#     cached_marks_summary = models.JSONField(blank=True, null=True)
#     cached_applicant_data = models.JSONField(blank=True, null=True)
#     cache_updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ['-created_at']
#         unique_together = ['proposal', 'applicant', 'evaluator']
#         indexes = [
#             models.Index(fields=["cached_status", "-created_at"]),
#         ]

#     def __str__(self):
#         return f"Presentation {self.proposal.proposal_id} by {self.applicant.get_full_name()}"

#     @property
#     def is_ready_for_evaluation(self):
#         return (
#             self.document_uploaded and
#             self.evaluator and
#             self.final_decision == 'assigned'
#         )

#     @property
#     def is_evaluation_completed(self):
#         return (
#             self.evaluator_marks is not None and
#             self.evaluated_at is not None
#         )

#     @property
#     def can_make_final_decision(self):
#         return (
#             self.is_evaluation_completed and
#             self.final_decision in ['evaluated']
#         )

#     def update_evaluator_info(self, evaluator_user):
#         self.evaluator = evaluator_user
#         self.save(update_fields=['evaluator'])

#     def submit_evaluation(self, marks, remarks):
#         self.evaluator_marks = marks
#         self.evaluator_remarks = remarks
#         self.evaluated_at = timezone.now()
#         self.final_decision = 'evaluated'
#         self.save(update_fields=[
#             'evaluator_marks',
#             'evaluator_remarks',
#             'evaluated_at',
#             'final_decision'
#         ])

#     def update_admin_decision(self, admin_user, decision, remarks=None):
#         self.final_decision = decision
#         self.admin_remarks = remarks
#         self.admin = admin_user
#         self.admin_evaluated_at = timezone.now()
#         self.save(update_fields=[
#             'final_decision',
#             'admin_remarks',
#             'admin',
#             'admin_evaluated_at'
#         ])

#     def assign_materials(self, video_file=None, video_link=None, document_file=None, presentation_date=None, admin_user=None):
#         if video_link:
#             self.video_link = video_link
#         if video_file:
#             self.video = video_file
#         if document_file:
#             self.document = document_file
#         if presentation_date:
#             self.presentation_date = presentation_date

#         if admin_user:
#             self.admin = admin_user
#             self.admin_evaluated_at = timezone.now()

#         has_video = bool(self.video or self.video_link)
#         has_document = bool(self.document)
#         has_date = bool(self.presentation_date)

#         if has_video and has_document and has_date:
#             self.document_uploaded = True
#             if self.final_decision == 'pending':
#                 self.final_decision = 'assigned'

#         self.save()

#     def save(self, *args, **kwargs):
#         skip_cache_update = kwargs.pop("skip_cache_update", False)
#         has_video = bool(self.video or self.video_link)
#         has_document = bool(self.document)
#         has_date = bool(self.presentation_date)

#         if has_video and has_document and has_date:
#             self.document_uploaded = True
#             if self.final_decision == 'pending':
#                 self.final_decision = 'assigned'
#         else:
#             self.document_uploaded = False
#             if self.final_decision == 'assigned' and not (has_video and has_document and has_date):
#                 self.final_decision = 'pending'
#         super().save(*args, **kwargs)

#     def update_cached_values(self, save=True):
#         """Populate cache fields for fast API response."""
#         self.cached_evaluator_name = self.evaluator.get_full_name() if self.evaluator else None
#         self.cached_status = self.final_decision
#         self.cached_marks_summary = {
#             "marks": float(self.evaluator_marks) if self.evaluator_marks is not None else None,
#             "remarks": self.evaluator_remarks,
#             "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
#         }
#         if self.applicant:
#             self.cached_applicant_data = {
#                 "id": self.applicant.id,
#                 "name": self.applicant.get_full_name() if hasattr(self.applicant, "get_full_name") else str(self.applicant),
#                 "email": getattr(self.applicant, "email", None),
#             }
#         else:
#             self.cached_applicant_data = {}
#         self.cache_updated_at = timezone.now()
#         if save:
#             self._disable_signal = True      # <<< Set attribute before saving
#             self.save(update_fields=[
#                 "cached_status", "cached_evaluator_name",
#                 "cached_marks_summary", "cached_applicant_data", "cache_updated_at"
#             ])
#             del self._disable_signal         # <<< Remove it after

# # ---- Signal to auto-update cache fields ----
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver

# @receiver([post_save, post_delete], sender=Presentation)
# def auto_update_presentation_cache(sender, instance, **kwargs):
#     if getattr(instance, "_disable_signal", False):
#         # Signal called by a save() that is doing only a cache update: do nothing!
#         return
#     instance.update_cached_values()
