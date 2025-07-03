from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from dynamic_form.models import ApplicationStatusHistory  # Adjust the import path as needed
from notifications.utils import send_notification

@receiver(post_save, sender=ApplicationStatusHistory)
def notify_on_status_change(sender, instance, created, **kwargs):
    if created:
        submission = instance.submission
        applicant = submission.applicant
        if not applicant:
            return  # No notification if there is no applicant linked.

        message = (
            f"Your application ({submission.proposal_id}) status changed from "
            f"{instance.previous_status} to {instance.new_status}. Comments: "
            f"{instance.comment or 'No additional info'}."
        )
        subject = "Application Status Update"

        # Sending email using Django's send_mail function
        if applicant.email:
            send_mail(
                subject,
                message,
                'noreply@example.com',  # Update with your sender email
                [applicant.email],
                fail_silently=False,
            )

        # Use the notification utility
        send_notification(
            recipient=applicant,
            message=message,
            notification_type='status_update'
        )
