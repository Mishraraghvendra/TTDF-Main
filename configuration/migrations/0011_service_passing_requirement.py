# Generated by Django 5.1.4 on 2025-07-04 09:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_eval', '0004_alter_questionevaluation_assignment'),
        ('configuration', '0010_remove_service_is_active_service_is_stopped_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='passing_requirement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='services', to='app_eval.passingrequirement'),
        ),
    ]
