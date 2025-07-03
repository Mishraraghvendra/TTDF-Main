# applicant_dashboard/models.py - 

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from dynamic_form.models import FormSubmission
import uuid

User = get_user_model()


class DashboardStats(models.Model):
    """
    Model to cache dashboard statistics for better performance
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dashboard_stats')
    total_proposals = models.PositiveIntegerField(default=0)
    approved_proposals = models.PositiveIntegerField(default=0)
    under_evaluation = models.PositiveIntegerField(default=0)
    not_shortlisted = models.PositiveIntegerField(default=0)
    draft_applications = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dashboard stats for {self.user.email}"

    def refresh_stats(self):
        """Refresh dashboard statistics using the same categorization logic"""
        # Get all proposals for this user (excluding drafts)
        proposals = FormSubmission.objects.filter(applicant=self.user).exclude(status=FormSubmission.DRAFT)
        
        # Initialize counters
        total = proposals.count()
        approved = 0
        under_eval = 0
        not_shortlisted = 0
        
        # Categorize each proposal using the same logic as ProposalStatsAPIView
        for proposal in proposals:
            category = self._categorize_proposal(proposal)
            
            if category == 'Approved':
                approved += 1
            elif category in ['Evaluation', 'Interview']:
                under_eval += 1
            elif category == 'Not Shortlisted':
                not_shortlisted += 1
            # Note: 'Submitted', 'Screening', 'History' are not counted in dashboard stats
        
        # Update stats
        self.total_proposals = total
        self.approved_proposals = approved
        self.under_evaluation = under_eval
        self.not_shortlisted = not_shortlisted
        
        # Count drafts
        self.draft_applications = FormSubmission.objects.filter(
            applicant=self.user, 
            status=FormSubmission.DRAFT
        ).count()
        
        self.save()

    def _categorize_proposal(self, proposal):
        """Use the same categorization logic as ProposalStatsAPIView"""
        # Get workflow records
        latest_screening = proposal.screening_records.order_by('-cycle').first()
        tech_eval = proposal.technical_evaluation_rounds.first()
        presentation = proposal.presentations.first()

        # PRIORITY 1: Check presentation final_decision first (if exists)
        if presentation:
            if presentation.final_decision == 'shortlisted':
                return 'Approved'
            elif presentation.final_decision in ['not_shortlisted', 'rejected']:
                return 'Not Shortlisted'
            elif presentation.final_decision in ['pending', 'assigned', 'evaluated']:
                return 'Interview'

        # PRIORITY 2: Check FormSubmission status for definitive states
        if proposal.status == FormSubmission.APPROVED:
            return 'Approved'
        elif proposal.status == FormSubmission.REJECTED:
            return 'Not Shortlisted'

        # PRIORITY 3: For SUBMITTED status, follow the workflow logic
        if proposal.status == FormSubmission.SUBMITTED:
            # Check if we have any screening
            if not latest_screening:
                return 'Submitted'
            
            # Check admin screening decision
            if latest_screening.admin_decision == 'pending':
                return 'Submitted'
            elif latest_screening.admin_decision == 'not shortlisted':
                return 'Not Shortlisted'
            elif latest_screening.admin_decision == 'shortlisted':
                # Check technical screening
                tech_record = getattr(latest_screening, 'technical_record', None)
                if not tech_record:
                    return 'Screening'
                
                if tech_record.technical_decision == 'pending':
                    return 'Screening'
                elif tech_record.technical_decision == 'not shortlisted':
                    return 'Not Shortlisted'
                elif tech_record.technical_decision == 'shortlisted':
                    # Check technical evaluation
                    if not tech_eval:
                        return 'Evaluation'
                    
                    if tech_eval.assignment_status == 'pending':
                        return 'Evaluation'
                    elif tech_eval.assignment_status == 'assigned':
                        return 'Evaluation'
                    elif tech_eval.assignment_status == 'completed':
                        if tech_eval.overall_decision == 'recommended':
                            # Should have presentation at this point
                            if not presentation:
                                return 'Interview'  # Waiting for presentation creation
                            # Presentation cases handled in PRIORITY 1 above
                            return 'Interview'
                        elif tech_eval.overall_decision == 'not_recommended':
                            return 'Not Shortlisted'
                        else:  # pending
                            return 'Evaluation'
                    else:
                        return 'Evaluation'
                else:
                    return 'Not Shortlisted'
            else:
                return 'Not Shortlisted'
        
        # Default case
        return 'History'


class UserActivity(models.Model):
    """
    Model to track user activities and updates
    """
    ACTIVITY_TYPES = [
        ('proposal_submitted', 'Proposal Submitted'),
        ('proposal_approved', 'Proposal Approved'),
        ('proposal_rejected', 'Proposal Rejected'),
        ('evaluation_started', 'Evaluation Started'),
        ('technical_review', 'Technical Review'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('documents_requested', 'Documents Requested'),
        ('call_published', 'New Call Published'),
        ('system_update', 'System Update'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    related_submission = models.ForeignKey(
        FormSubmission, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='user_activities'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    @property
    def time_ago(self):
        """Return human-readable time difference"""
        now = timezone.now()
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"


class DraftApplication(models.Model):
    """
    Model to track draft applications with progress
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='draft_apps')
    submission = models.OneToOneField(
        FormSubmission, 
        on_delete=models.CASCADE, 
        related_name='draft_progress'
    )
    progress_percentage = models.PositiveIntegerField(default=0)
    last_section_completed = models.CharField(max_length=100, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Draft: {self.submission.subject or 'Untitled'} - {self.progress_percentage}%"

    def calculate_progress(self):
        """Calculate completion percentage based on filled fields"""
        submission = self.submission
        total_fields = 0
        completed_fields = 0
        
        # Count required fields that are filled
        required_fields = [
            'individual_pan', 'applicant_type', 'abstract', 'novelty',
            'technical_feasibility', 'potential_impact', 'commercialization_strategy'
        ]
        
        for field in required_fields:
            total_fields += 1
            if getattr(submission, field, None):
                completed_fields += 1
        
        # Check for file uploads
        file_fields = ['pan_file', 'resume_upload']
        for field in file_fields:
            total_fields += 1
            if getattr(submission, field, None):
                completed_fields += 1
        
        self.progress_percentage = int((completed_fields / total_fields) * 100) if total_fields > 0 else 0
        self.save()
        return self.progress_percentage