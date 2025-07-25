# Generated by Django 5.1.4 on 2025-07-03 09:27

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("milestones", "0005_milestone_activities"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name="milestone",
            name="activities",
        ),
        migrations.AddField(
            model_name="milestone",
            name="start_date",
            field=models.DateField(
                blank=True, help_text="Milestone start date", null=True
            ),
        ),
        migrations.AddField(
            model_name="milestonedocument",
            name="mpr_for_month",
            field=models.DateField(
                blank=True,
                help_text="Month this MPR covers (any date in the target month)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="milestonedocument",
            name="remarks",
            field=models.TextField(
                blank=True,
                help_text="Additional remarks for milestone documents",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="proposalmoudocument",
            name="is_mou_signed",
            field=models.BooleanField(
                default=False, help_text="Mark as True when MOU is signed"
            ),
        ),
        migrations.AddField(
            model_name="submilestone",
            name="remarks",
            field=models.TextField(
                blank=True,
                help_text="Additional remarks for submilestone documents",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="submilestonedocument",
            name="mpr_for_month",
            field=models.DateField(
                blank=True,
                help_text="Month this MPR covers (any date in the target month)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="submilestonedocument",
            name="remarks",
            field=models.TextField(
                blank=True,
                help_text="Document description/remarks for submilestone documents",
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="ImplementationAgency",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("assigned_proposals", models.JSONField(blank=True, default=list)),
                (
                    "admin",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ia_admin_agency",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "users",
                    models.ManyToManyField(
                        blank=True,
                        related_name="ia_agencies",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
