# Generated by Django 5.1.4 on 2025-07-15 05:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dynamic_form", "0018_alter_collaborator_collaborator_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="collaborator",
            name="ttdf_company",
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
    ]
