# Generated by Django 5.1.6 on 2025-05-26 07:28

import django.core.serializers.json
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('delete', 'Delete'), ('login', 'Login')], max_length=20)),
                ('app_label', models.CharField(max_length=100)),
                ('model_name', models.CharField(max_length=100)),
                ('object_pk', models.CharField(blank=True, max_length=255, null=True)),
                ('object_repr', models.CharField(blank=True, max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('changes', models.JSONField(blank=True, encoder=django.core.serializers.json.DjangoJSONEncoder, help_text='Snapshot of model fields at time of action', null=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]
