import csv
import uuid
import re

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

def extract_emails(s):
    """Extract all emails from a string."""
    # Regex for emails inside parentheses or plain
    return re.findall(r'[\w\.-]+@[\w\.-]+', s)

def normalize_header(header):
    return header.strip().lower().replace(' ', '_').replace('\ufeff', '')

class Command(BaseCommand):
    help = 'Import Service, Committee, and Committee Members from CSV with committee as members list.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file to import')

    def handle(self, *args, **options):
        from configuration.models import Service, ScreeningCommittee, CommitteeMember

        csv_path = options['csv_path']
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            header_map = {normalize_header(col): col for col in reader.fieldnames}

            def val(row, *names, default=''):
                """Try multiple possible column names; fallback to default if all missing."""
                for name in names:
                    key = header_map.get(normalize_header(name))
                    if key and row.get(key):
                        return str(row.get(key)).strip()
                return default

            for row in reader:
                print("CSV Row:", row)  # Debug

                service_name = val(row, 'service', 'Service Name', 'Service')
                committee_members_raw = val(row, 'committee', 'Committee')
                committee_type = 'administrative'
                committee_name = f"{service_name} Administrative"

                if not service_name:
                    self.stdout.write(self.style.WARNING("Skipping row: No service name found"))
                    continue

                # --- Service ---
                service, service_created = Service.objects.get_or_create(
                    name=service_name,
                    defaults={
                        'description': f'Imported from CSV',
                        'is_active': True,
                        'created_by': None,
                    }
                )
                self.stdout.write(self.style.SUCCESS(
                    f"{'Created' if service_created else 'Exists'} Service: {service.name}"
                ))

                # --- ScreeningCommittee ---
                committee, com_created = ScreeningCommittee.objects.get_or_create(
                    service=service,
                    committee_type=committee_type,
                    defaults={
                        'name': committee_name,
                        'is_active': True,
                        'created_by': None,
                    }
                )
                self.stdout.write(self.style.SUCCESS(
                    f"{'Created' if com_created else 'Exists'} Committee: {committee.name}"
                ))

                # --- Committee Members ---
                emails = extract_emails(committee_members_raw)
                for member_email in emails:
                    member_email = member_email.lower()
                    user = User.objects.filter(email__iexact=member_email).first()
                    if not user:
                        user = User.objects.create(
                            email=member_email,
                            mobile=f"99999{str(uuid.uuid4())[:5]}",
                            full_name=member_email.split('@')[0],
                            gender='O',
                            is_active=True
                        )
                        self.stdout.write(self.style.WARNING(
                            f"Auto-created user: {member_email}"
                        ))
                    cm, cm_created = CommitteeMember.objects.get_or_create(
                        committee=committee,
                        user=user,
                        defaults={
                            'is_active': True,
                            'assigned_by': None,
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"{'Added' if cm_created else 'Exists'} Member: {member_email} to {committee.name}"
                    ))
