# applicant_dashboard/migrations/0001_initial.py

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dynamic_form', '0001_initial'),  # Adjust this number to match your actual dynamic_form migration
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DashboardStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_proposals', models.PositiveIntegerField(default=0)),
                ('approved_proposals', models.PositiveIntegerField(default=0)),
                ('under_evaluation', models.PositiveIntegerField(default=0)),
                ('not_shortlisted', models.PositiveIntegerField(default=0)),
                ('draft_applications', models.PositiveIntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='dashboard_stats', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('activity_type', models.CharField(choices=[
                    ('proposal_submitted', 'Proposal Submitted'),
                    ('proposal_approved', 'Proposal Approved'),
                    ('proposal_rejected', 'Proposal Rejected'),
                    ('evaluation_started', 'Evaluation Started'),
                    ('technical_review', 'Technical Review'),
                    ('interview_scheduled', 'Interview Scheduled'),
                    ('documents_requested', 'Documents Requested'),
                    ('call_published', 'New Call Published'),
                    ('system_update', 'System Update'),
                ], max_length=50)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('related_submission', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_activities', to='dynamic_form.formsubmission')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='DraftApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('progress_percentage', models.PositiveIntegerField(default=0)),
                ('last_section_completed', models.CharField(blank=True, max_length=100)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('submission', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='draft_progress', to='dynamic_form.formsubmission')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='draft_apps', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]