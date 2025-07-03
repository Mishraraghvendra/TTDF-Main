# applicant_dashboard/management/commands/populate_dashboard.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from applicant_dashboard.models import DashboardStats, UserActivity, DraftApplication
from dynamic_form.models import FormSubmission
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate dashboard with existing data and create sample activities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--refresh-stats',
            action='store_true',
            help='Refresh dashboard stats for all users',
        )
        parser.add_argument(
            '--create-sample-activities',
            action='store_true',
            help='Create sample activities for testing',
        )
        parser.add_argument(
            '--create-drafts',
            action='store_true',
            help='Create draft applications from existing draft submissions',
        )

    def handle(self, *args, **options):
        if options['refresh_stats']:
            self.refresh_all_stats()
        
        if options['create_sample_activities']:
            self.create_sample_activities()
            
        if options['create_drafts']:
            self.create_draft_applications()

    def refresh_all_stats(self):
        """Refresh dashboard stats for all users"""
        self.stdout.write('Refreshing dashboard stats...')
        
        users = User.objects.all()
        for user in users:
            stats, created = DashboardStats.objects.get_or_create(user=user)
            stats.refresh_stats()
            
            if created:
                self.stdout.write(f'Created stats for {user.email}')
            else:
                self.stdout.write(f'Updated stats for {user.email}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully refreshed stats for {users.count()} users')
        )

    def create_sample_activities(self):
        """Create sample activities for users with submissions"""
        self.stdout.write('Creating sample activities...')
        
        users_with_submissions = User.objects.filter(form_submissions__isnull=False).distinct()
        
        sample_activities = [
            {
                'activity_type': 'proposal_approved',
                'title': 'Proposal Approved',
                'description': 'Your proposal for "5G Rural Connectivity" has been approved and moved to implementation phase.',
            },
            {
                'activity_type': 'call_published',
                'title': 'New Call Published',
                'description': 'A new call for "AI in Telecom" has been published. Deadline: 2024-04-15',
            },
            {
                'activity_type': 'evaluation_started',
                'title': 'Evaluation Started',
                'description': 'Your proposal "Quantum Encryption" has started technical evaluation.',
            }
        ]
        
        for user in users_with_submissions[:5]:  # Limit to first 5 users
            for i, activity_data in enumerate(sample_activities):
                UserActivity.objects.get_or_create(
                    user=user,
                    activity_type=activity_data['activity_type'],
                    title=activity_data['title'],
                    defaults={
                        'description': activity_data['description'],
                        'created_at': timezone.now() - timedelta(hours=i*2)
                    }
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created sample activities for {users_with_submissions.count()} users')
        )

    def create_draft_applications(self):
        """Create draft applications from existing draft submissions"""
        self.stdout.write('Creating draft applications...')
        
        draft_submissions = FormSubmission.objects.filter(status=FormSubmission.DRAFT)
        created_count = 0
        
        for submission in draft_submissions:
            if submission.applicant:
                draft, created = DraftApplication.objects.get_or_create(
                    user=submission.applicant,
                    submission=submission
                )
                if created:
                    draft.calculate_progress()
                    created_count += 1
                    self.stdout.write(f'Created draft for {submission.form_id}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} draft applications')
        )