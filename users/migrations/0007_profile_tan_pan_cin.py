# Generated by Django 5.1.4 on 2025-07-05 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_profile_id_number_profile_id_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='tan_pan_cin',
            field=models.FileField(blank=True, null=True, upload_to='org/tan_pan_cin/'),
        ),
    ]
