# Generated by Django 5.1.6 on 2025-07-22 02:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_form', '0024_formsubmission_actual_contribution_applicant'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='teammember',
            unique_together={('form_submission', 'name', 'otherdetails')},
        ),
    ]
