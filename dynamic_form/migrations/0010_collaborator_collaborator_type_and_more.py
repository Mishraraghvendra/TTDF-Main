# Generated by Django 5.1.6 on 2025-07-11 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_form', '0009_remove_formsubmission_based_on_ipr_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='collaborator',
            name='collaborator_type',
            field=models.CharField(blank=True, choices=[('principalApplicant', 'principalApplicant'), ('consortiumPartner', 'principalApplicant')], max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='subshareholder',
            name='organization_name_subholder',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
