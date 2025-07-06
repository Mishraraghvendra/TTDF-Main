from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from dynamic_form.models import FormTemplate, FormPage, FormField

class Command(BaseCommand):
    help = "Create Samriddh Gram Pilot Application Form (only fields not in User/Profile/Milestone)"

    def handle(self, *args, **options):
        template, created = FormTemplate.objects.get_or_create(
            title="Samriddh Gram Pilot Application Form",
            defaults={
                "is_active": True,
                "start_date": timezone.now(),
                "end_date": timezone.now() + timedelta(days=120),
            }
        )
        self.stdout.write(self.style.SUCCESS(f"FormTemplate: {template.title}"))

        pages_and_fields = [
            {
                "page": {"title": "Proposal Details", "order": 1},
                "fields": [
                    {"label": "Proposal Duration (In Months)", "field_type": "number", "required": True, "order": 1},
                    {"label": "Organization Type", "field_type": "dropdown", "required": True, "order": 2, "options": {"choices": ["For profit", "Not-for profit"]}},
                    {"label": "Proposal Submitted By", "field_type": "text", "required": True, "order": 3, "help_text": "Primary Applicant only"},
                    {"label": "Registration Certificate Attachment", "field_type": "file", "required": True, "order": 4, "help_text": ".pdf only", "options": {"file_types": ["pdf"]}},
                    {"label": "Company As per CfP", "field_type": "dropdown", "required": True, "order": 5, "options": {"choices": [
                        "Domestic Company(ies) with focus on telecom R&D, Use case development",
                        "Startups / MSMEs",
                        "Academic institutions",
                        "R&D institutions, Section 8 companies / Societies, Central & State government entities / PSUs /Autonomous Bodies/SPVs / Limited liability partnerships"
                    ]}},
                    {"label": "CA Certified Shareholding Pattern Attachment", "field_type": "file", "required": True, "order": 6, "help_text": ".pdf", "options": {"file_types": ["pdf"]}},
                    {"label": "DSIR Certificate Attachment (If applicable)", "field_type": "file", "required": False, "order": 7, "help_text": ".pdf", "options": {"file_types": ["pdf"]}},
                    {"label": "TAN PAN CIN Attachment", "field_type": "file", "required": True, "order": 8, "help_text": ".pdf", "options": {"file_types": ["pdf"]}},
                ]
            },
            {
                "page": {"title": "Collaborator Details", "order": 2},
                "fields": [
                    {
                        "label": "Collaborators",
                        "field_type": "table",
                        "required": False,
                        "order": 1,
                        "options": {
                            "columns": [
                                {"label": "Contact Person Name", "type": "text", "required": True},
                                {"label": "Organisation Name", "type": "text", "required": True},
                                {"label": "Organization Type", "type": "dropdown", "choices": ["For profit", "Not-for profit"], "required": True},
                                {"label": "MOU File", "type": "file", "file_types": ["pdf"], "required": True},
                            ],
                            "min_rows": 1,
                            "max_rows": 10
                        }
                    }
                ]
            },
            {
                "page": {"title": "Shareholder Details", "order": 3},
                "fields": [
                    {
                        "label": "Principal Applicant Shareholders",
                        "field_type": "table",
                        "required": False,
                        "order": 1,
                        "options": {
                            "columns": [
                                {"label": "Share Holder Name", "type": "text", "required": True},
                                {"label": "Percentage of Share", "type": "number", "required": True, "validation": {"min": 0, "max": 100}},
                                {"label": "Passport/Aadhaar", "type": "file", "file_types": ["pdf"], "required": True},
                            ],
                            "min_rows": 1,
                            "max_rows": 20
                        }
                    },
                    {
                        "label": "Sub Applicant Shareholders (Each Sub Agency)",
                        "field_type": "table",
                        "required": False,
                        "order": 2,
                        "options": {
                            "columns": [
                                {"label": "Share Holder Name", "type": "text", "required": True},
                                {"label": "Percentage of Share", "type": "number", "required": True, "validation": {"min": 0, "max": 100}},
                                {"label": "Passport/Aadhaar", "type": "file", "file_types": ["pdf"], "required": True},
                            ],
                            "min_rows": 1,
                            "max_rows": 20
                        },
                        "help_text": "Repeat for each sub applicant (up to 10)"
                    },
                    {"label": "Is Applied in TTDF Before?", "field_type": "dropdown", "required": True, "order": 3, "options": {"choices": ["Yes", "No"]}},
                ]
            },
            {
                "page": {"title": "Fund Details", "order": 4},
                "fields": [
                    {"label": "Is There Any Outstanding Loan?", "field_type": "dropdown", "required": True, "order": 1, "options": {"choices": ["Yes", "No"]}},
                    {"label": "Loan Description", "field_type": "text", "required": False, "order": 2},
                    {"label": "Loan Documents", "field_type": "file", "required": False, "order": 3, "help_text": ".pdf format", "options": {"file_types": ["pdf"], "multiple": True}},
                    {"label": "Loan Amount", "field_type": "number", "required": False, "order": 4},
                ]
            },
            {
                "page": {"title": "Finance & Contributions", "order": 5},
                "fields": [
                    {
                        "label": "Contribution Items",
                        "field_type": "table",
                        "required": False,
                        "order": 1,
                        "options": {
                            "columns": [
                                {"label": "Contribution Item", "type": "text", "required": True},
                                {"label": "Contribution Amount", "type": "number", "required": True},
                            ],
                            "min_rows": 1
                        }
                    },
                    {
                        "label": "Fund Items",
                        "field_type": "table",
                        "required": False,
                        "order": 2,
                        "options": {
                            "columns": [
                                {"label": "Fund Item", "type": "text", "required": True},
                                {"label": "Fund Amount", "type": "number", "required": True},
                            ],
                            "min_rows": 1
                        }
                    },
                    {"label": "Grants from TTDF (INR)", "field_type": "number", "required": False, "order": 3},
                    {"label": "Contribution by Applicant (INR)", "field_type": "number", "required": False, "order": 4},
                    {"label": "Expected other source for contribution (INR)", "field_type": "number", "required": False, "order": 5},
                    {"label": "Details of the other sources of funding (INR)", "field_type": "number", "required": False, "order": 6},
                    {"label": "Total Project Cost (INR)", "field_type": "number", "required": False, "order": 7, "help_text": "Sum total of all above."},
                ]
            }
        ]

        for page_def in pages_and_fields:
            page_obj, _ = FormPage.objects.get_or_create(
                form_template=template,
                title=page_def["page"]["title"],
                defaults={"order": page_def["page"]["order"]}
            )
            self.stdout.write(self.style.SUCCESS(f"Page: {page_obj.title}"))

            for field_def in page_def["fields"]:
                ff_defaults = {
                    "field_type": field_def.get("field_type", "text"),
                    "required": field_def.get("required", False),
                    "placeholder": field_def.get("placeholder", ""),
                    "help_text": field_def.get("help_text", ""),
                    "order": field_def.get("order", 1),
                    "options": field_def.get("options", None),
                    "validation": field_def.get("validation", None),
                }
                field_obj, _ = FormField.objects.get_or_create(
                    page=page_obj,
                    label=field_def["label"],
                    defaults=ff_defaults,
                )
                self.stdout.write(f"  Field: {field_obj.label}")

        self.stdout.write(self.style.SUCCESS("✅ Samriddh Gram Pilot dynamic form template created!"))
