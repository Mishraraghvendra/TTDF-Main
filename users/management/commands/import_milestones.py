import csv
from django.core.management.base import BaseCommand
from dynamic_form.models import FormSubmission
from milestones.models import Milestone, SubMilestone

def parse_int(val):
    try:
        return int(val)
    except Exception:
        return 0

class Command(BaseCommand): 
    help = "Import milestones (and submilestones) from CSV proposal-wise, putting Activities in activities field ONLY."

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to CSV file')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        with open(csv_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            self.stdout.write(self.style.WARNING(f"Detected columns: {reader.fieldnames}"))
            for idx, row in enumerate(reader):
                proposal_id = row.get('ID', '').strip()
                title = row.get('Milestone', '').strip()
                description = (row.get('Work') or '').strip()
                activities = (row.get('Activities') or '').strip()
                revised_time_required = parse_int(row.get('Time (Months)', 0))
                revised_contri_applicant = parse_int(row.get('Applicant Contribution', 0))
                revised_grant_from_ttdf = parse_int(row.get('TTDF Grants', 0))
                funds_requested= parse_int(row.get('Funds Requested', 0))

                if not (proposal_id and title):
                    self.stdout.write(self.style.ERROR(f"[Row {idx+2}] Missing proposal ID or milestone title. Skipping."))
                    continue

                try:
                    proposal = FormSubmission.objects.get(proposal_id=proposal_id)
                except FormSubmission.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"[Row {idx+2}] Proposal {proposal_id} not found. Skipping."))
                    continue

                # Create or update Milestone
                milestone, created = Milestone.objects.get_or_create(
                    proposal=proposal,
                    title=title,
                    defaults={
                        'description': description,
                        'revised_time_required': revised_time_required,
                        'revised_contri_applicant': revised_contri_applicant,
                        'revised_grant_from_ttdf': revised_grant_from_ttdf,
                        'time_required': revised_time_required,
                        'funds_requested': 0,
                        'grant_from_ttdf': revised_grant_from_ttdf,
                        'initial_contri_applicant': revised_contri_applicant,
                        'initial_grant_from_ttdf': revised_grant_from_ttdf,
                        'activities': activities,
                    }
                )
                # Update if already exists
                if not created:
                    updated = False
                    for field, value in [
                        ('description', description),
                        ('revised_time_required', revised_time_required),
                        ('revised_contri_applicant', revised_contri_applicant),
                        ('revised_grant_from_ttdf', revised_grant_from_ttdf),
                        ('activities', activities),
                    ]:
                        if getattr(milestone, field) != value:
                            setattr(milestone, field, value)
                            updated = True
                    if updated:
                        milestone.save()
                        self.stdout.write(self.style.SUCCESS(f"[Row {idx+2}] Updated Milestone '{title}' for {proposal_id}"))
                    else:
                        self.stdout.write(f"[Row {idx+2}] Milestone '{title}' for {proposal_id} already up to date.")
                else:
                    self.stdout.write(self.style.SUCCESS(f"[Row {idx+2}] Created Milestone '{title}' for {proposal_id}"))

                # Submilestone logic (if your CSV has submilestone columns)
                sub_title = row.get('Submilestone', '').strip()
                if sub_title:
                    sub_description = row.get('Subwork', '').strip()
                    sub_time = parse_int(row.get('Subtime', 0))
                    sub_contri = parse_int(row.get('SubApplicantContribution', 0))
                    sub_grant = parse_int(row.get('SubTTDFGrants', 0))

                    submilestone, sub_created = SubMilestone.objects.get_or_create(
                        milestone=milestone,
                        title=sub_title,
                        defaults={
                            'description': sub_description,
                            'revised_time_required': sub_time,
                            'revised_contri_applicant': sub_contri,
                            'revised_grant_from_ttdf': sub_grant,
                            'time_required': sub_time,
                            'grant_from_ttdf': sub_grant,
                            'initial_contri_applicant': sub_contri,
                            'initial_grant_from_ttdf': sub_grant,
                        }
                    )
                    if not sub_created:
                        updated = False
                        for field, value in [
                            ('description', sub_description),
                            ('revised_time_required', sub_time),
                            ('revised_contri_applicant', sub_contri),
                            ('revised_grant_from_ttdf', sub_grant),
                        ]:
                            if getattr(submilestone, field) != value:
                                setattr(submilestone, field, value)
                                updated = True
                        if updated:
                            submilestone.save()
                            self.stdout.write(self.style.SUCCESS(f"[Row {idx+2}] Updated SubMilestone '{sub_title}'"))
                        else:
                            self.stdout.write(f"[Row {idx+2}] SubMilestone '{sub_title}' already up to date.")
                    else:
                        self.stdout.write(self.style.SUCCESS(f"[Row {idx+2}] Created SubMilestone '{sub_title}'"))

        self.stdout.write(self.style.SUCCESS("Milestone and SubMilestone import completed!"))
