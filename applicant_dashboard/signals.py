# applicant_dashboard/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from dynamic_form.models import FormSubmission
from .models import DashboardStats, UserActivity, DraftApplication


@receiver(post_save, sender=FormSubmission)
def update_dashboard_on_submission_change(sender, instance, created, **kwargs):
    """
    Update dashboard stats and create activities when FormSubmission changes
    """
    if not instance.applicant:
        return
    
    # Update dashboard stats
    stats, _ = DashboardStats.objects.get_or_create(user=instance.applicant)
    stats.refresh_stats()
    
    # Create/update draft application if status is DRAFT
    if instance.status == FormSubmission.DRAFT:
        draft, created = DraftApplication.objects.get_or_create(
            user=instance.applicant,
            submission=instance
        )
        if not created:
            draft.calculate_progress()
    else:
        # Remove from drafts if no longer draft
        DraftApplication.objects.filter(submission=instance).delete()
    
    # Create activity based on status change
    if created and instance.status == FormSubmission.SUBMITTED:
        UserActivity.objects.create(
            user=instance.applicant,
            activity_type='proposal_submitted',
            title='Proposal Submitted',
            description=f'Your proposal "{instance.subject or instance.form_id}" has been submitted successfully.',
            related_submission=instance
        )


@receiver(pre_save, sender=FormSubmission)
def track_status_changes(sender, instance, **kwargs):
    """
    Track status changes and create appropriate activities
    """
    if not instance.pk or not instance.applicant:
        return
    
    try:
        old_instance = FormSubmission.objects.get(pk=instance.pk)
        old_status = old_instance.status
        new_status = instance.status
        
        if old_status != new_status:
            activity_map = {
                (FormSubmission.SUBMITTED, FormSubmission.EVALUATED): {
                    'type': 'evaluation_started',
                    'title': 'Admin Screening Started',
                    'description': 'Your proposal has started admin screening process.'
                },
                (FormSubmission.EVALUATED, FormSubmission.TECHNICAL): {
                    'type': 'technical_review',
                    'title': 'Technical Evaluation Started',
                    'description': 'Your proposal has moved to technical evaluation phase.'
                },
                (FormSubmission.TECHNICAL, FormSubmission.APPROVED): {
                    'type': 'proposal_approved',
                    'title': 'Proposal Approved',
                    'description': 'Congratulations! Your proposal has been approved.'
                },
                (FormSubmission.TECHNICAL, FormSubmission.REJECTED): {
                    'type': 'proposal_rejected',
                    'title': 'Proposal Not Selected',
                    'description': 'Your proposal was not selected for this round.'
                },
            }
            
            activity_data = activity_map.get((old_status, new_status))
            if activity_data:
                UserActivity.objects.create(
                    user=instance.applicant,
                    activity_type=activity_data['type'],
                    title=activity_data['title'],
                    description=activity_data['description'],
                    related_submission=instance
                )
    
    except FormSubmission.DoesNotExist:
        pass


# Auto-create dashboard stats for new users
from django.contrib.auth import get_user_model
User = get_user_model()

@receiver(post_save, sender=User)
def create_dashboard_stats(sender, instance, created, **kwargs):
    """Create dashboard stats for new users"""
    if created:
        DashboardStats.objects.create(user=instance)