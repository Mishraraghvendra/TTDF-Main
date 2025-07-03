import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from dynamic_form.models import FormSubmission
from configuration.models import Service , ScreeningCommittee, CommitteeMember, ScreeningResult


User = get_user_model()

class Command(BaseCommand):
    help = 'Import committees and members from CSV and assign to proposals.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file to import')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, start=2):
                # --- FIELDS ---
                service_name = row.get('service', '').strip()
                committee_name = row.get('name', '').strip()
                committee_type = row.get('committee_type', '').strip().lower()
                if not committee_type:
                    committee_type = 'technical'
                    self.stdout.write(self.style.WARNING(
                        f"Row {row_num}: Missing committee_type. Defaulted to 'technical'."
                    ))
                is_active = row.get('is_active', 'TRUE').strip().upper() == 'TRUE'
                user_email = row.get('user', '').strip()
                proposal_id = row.get('ID', '').strip()

                # --- GET/CREATE SERVICE ---
                if not service_name:
                    self.stdout.write(self.style.ERROR(f"Row {row_num}: Missing service name."))
                    continue
                service, _ = Service.objects.get_or_create(name=service_name)

                # --- CREATE COMMITTEE ---
                committee, created = ScreeningCommittee.objects.get_or_create(
                    service=service,
                    name=committee_name,
                    committee_type=committee_type,
                    defaults={'is_active': is_active}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(
                        f"Row {row_num}: Created committee {committee_name} for service {service_name} ({committee_type})"
                    ))
                else:
                    self.stdout.write(f"Row {row_num}: Found existing committee {committee_name} for service {service_name} ({committee_type})")

                # --- CREATE COMMITTEE MEMBER ---
                if user_email:
                    try:
                        user = User.objects.get(email=user_email)
                        cmember, cmem_created = CommitteeMember.objects.get_or_create(
                            committee=committee,
                            user=user,
                            defaults={'is_active': is_active}
                        )
                        if cmem_created:
                            self.stdout.write(self.style.SUCCESS(
                                f"Row {row_num}: Added {user.email} as member to {committee.name}"
                            ))
                    except User.DoesNotExist:
                        self.stdout.write(self.style.ERROR(
                            f"Row {row_num}: User {user_email} does not exist."
                        ))

                # --- ASSIGN COMMITTEE TO PROPOSAL IN SCREENINGRESULT ---
                if proposal_id:
                    try:
                        proposal = FormSubmission.objects.get(proposal_id=proposal_id)
                        ScreeningResult.objects.get_or_create(
                            application=proposal,
                            committee=committee
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f"Row {row_num}: Assigned committee to proposal {proposal_id}"
                        ))
                    except FormSubmission.DoesNotExist:
                        self.stdout.write(self.style.ERROR(
                            f"Row {row_num}: Proposal {proposal_id} does not exist."
                        ))
