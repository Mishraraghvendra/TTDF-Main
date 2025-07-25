# Generated by Django 5.1.6 on 2025-05-30 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_form', '0002_alter_formsubmission_details_source_funding_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='formsubmission',
            name='org_type',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='declaration_document',
            field=models.FileField(blank=True, null=True, upload_to='submissions/declarations/'),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='description',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='org_address_line1',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='org_approval_certificate',
            field=models.FileField(blank=True, null=True, upload_to='submissions/org_docs/'),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='org_city_town',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='org_mobile',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='org_official_email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='org_pin_code',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='org_registration_certificate',
            field=models.FileField(blank=True, null=True, upload_to='submissions/org_docs/'),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='org_state',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='org_street_village',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='org_tan_pan_cin_file',
            field=models.FileField(blank=True, null=True, upload_to='submissions/org_docs/'),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='pan_file',
            field=models.FileField(blank=True, null=True, upload_to='submissions/pan/'),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='passport_file',
            field=models.FileField(blank=True, null=True, upload_to='submissions/passport/'),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='resume_upload',
            field=models.FileField(blank=True, null=True, upload_to='submissions/resumes/'),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='subject',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
