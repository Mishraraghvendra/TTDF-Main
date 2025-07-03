# screening/models.py

import uuid
from django.conf import settings
from django.db import models
from datetime import datetime
from django.db.models import Max

# link to your static‐column proposal model
from dynamic_form.models import FormSubmission

STATUS_CHOICES = (
    ('pending',  'Pending'),
    ('shortlisted', 'Shortlisted'),
    ('not shortlisted', 'Not Shortlisted'),
) 

class ScreeningRecord(models.Model):
    """
    Tracks each admin‐screening pass for a given proposal.
    auto‐cycles, and snapshots key fields from the proposal.
    """
    proposal = models.ForeignKey(
        FormSubmission,
        on_delete=models.CASCADE,
        related_name='screening_records'
    )

    # Automatically incremented on save
    cycle = models.PositiveIntegerField(editable=False)

    # Snapshot from the FormSubmission at the time of screening
    subject        = models.CharField(max_length=255, blank=True)
    description    = models.TextField(blank=True)
    contact_name   = models.CharField(max_length=200, blank=True)
    contact_email  = models.EmailField(blank=True)

    # The user who performed the admin screening
    admin_evaluator  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_screenings"
    )
    admin_decision   = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_remarks    = models.TextField(blank=True, null=True)
    evaluated_document   = models.FileField(upload_to="screening/admin_docs/", null=True, blank=True)
    admin_screened_at= models.DateTimeField(auto_now_add=True)

    # once tech_screen is created, we mark this flag
    technical_evaluated = models.BooleanField(default=False)
    admin_evaluated = models.BooleanField(default=False)

    class Meta:
        unique_together = ('proposal', 'cycle')
        ordering = ['-cycle', '-admin_screened_at']

    def save(self, *args, **kwargs):
        if self._state.adding and not self.cycle:
            last_cycle = (
                ScreeningRecord.objects
                .filter(proposal=self.proposal)
                .aggregate(max_cycle=Max('cycle'))['max_cycle'] or 0
            )
            self.cycle = last_cycle + 1

            # Snapshot fields from the proposal
            self.subject       = getattr(self.proposal, 'subject', '')       or ''
            self.description   = getattr(self.proposal, 'description', '')   or ''
            self.contact_name  = getattr(self.proposal, 'contact_name', '')  or ''
            self.contact_email = getattr(self.proposal, 'contact_email', '') or ''

        # Mark as evaluated when admin makes decision
        if self.admin_decision in ['shortlisted', 'not shortlisted']:
            self.admin_evaluated = True
            
            # Create technical screening record ONLY when shortlisted
            if (self.admin_decision == 'shortlisted' and 
                not hasattr(self, 'technical_record')):
                try:
                    TechnicalScreeningRecord.objects.get_or_create(
                        screening_record=self,
                        defaults={'technical_decision': 'pending'}
                    )
                except:
                    # Handle case where technical record already exists
                    pass

        super().save(*args, **kwargs)

    def __str__(self):
        pid = self.proposal.proposal_id or self.proposal.form_id
        return f"{pid} (Cycle {self.cycle}) – Admin: {self.admin_decision}"

    @classmethod
    def get_or_create_for_proposal(cls, proposal, **kwargs):
        """Get existing record or create new one for proposal"""
        # Try to get the latest record for this proposal
        existing_record = cls.objects.filter(proposal=proposal).order_by('-cycle').first()
        
        if existing_record and not existing_record.admin_evaluated:
            # Return existing record if it hasn't been evaluated yet
            return existing_record, False
        else:
            # Create new record if none exists or if the latest one is already evaluated
            record = cls.objects.create(proposal=proposal, **kwargs)
            return record, True


class TechnicalScreeningRecord(models.Model):
    """
    One‐to‐one with each ScreeningRecord, holds the technical‐screen pass.
    """ 
    screening_record = models.OneToOneField(
        ScreeningRecord,
        on_delete=models.CASCADE,
        related_name="technical_record"
    )
    technical_evaluator  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="technical_screenings"
    )
    technical_decision   = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    technical_marks      = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    technical_remarks    = models.TextField(blank=True, null=True)
    technical_document   = models.FileField(upload_to="screening/technical_screening_docs/", null=True, blank=True)
    technical_screened_at= models.DateTimeField(auto_now_add=True)
    technical_evaluated = models.BooleanField(default=False)

    # Track creation and updates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-technical_screened_at']

    def save(self, *args, **kwargs):
        is_new_shortlist = (
           self.pk is None and self.technical_decision == 'shortlisted'
    )

        super().save(*args, **kwargs)

    # Create evaluation round AFTER saving
        if is_new_shortlist:
            try:
                from tech_eval.models import TechnicalEvaluationRound
                if not TechnicalEvaluationRound.objects.filter(proposal=self.screening_record.proposal).exists():
                    TechnicalEvaluationRound.objects.create(
                    proposal=self.screening_record.proposal,
                    assignment_status='pending'
                )
                    print(f"✅ Created evaluation round for {self.screening_record.proposal.proposal_id}")
            except Exception as e:
                   print(f"❌ Error creating evaluation round: {e}")


    def __str__(self):
        pid = self.screening_record.proposal.proposal_id or self.screening_record.proposal.form_id
        cyc = self.screening_record.cycle
        return f"{pid} (Cycle {cyc}) – Technical: {self.technical_decision}"
    

     