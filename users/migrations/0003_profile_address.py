# Generated by Django 5.1.6 on 2025-06-23 12:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_remove_profile_address_profile_address_line_1_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='address',
            field=models.TextField(blank=True),
        ),
    ]
