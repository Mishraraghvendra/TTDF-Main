import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Role
from django.db import transaction

User = get_user_model()

GENDER_MAP = {
    'male': 'M',
    'female': 'F',
    'others': 'O',
    'other': 'O',
}

DEFAULT_PASSWORD = 'Test@1234'

class Command(BaseCommand):
    help = "Import users from CSV. If role doesn't exist, create it. Sets default password."

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file')

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = options['csv_path']
        created_users = 0
        updated_users = 0
        created_roles = 0
        skipped_conflicts = 0

        with open(csv_path, encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, start=2):
                email = (row.get('email') or '').strip()
                mobile = (row.get('mobile') or '').strip()
                full_name = (row.get('full_name') or '').strip()
                gender_raw = (row.get('gender') or '').strip().lower()
                gender = GENDER_MAP.get(gender_raw)
                organization = (row.get('organization') or '').strip() if 'organization' in row else ''
                role_name = (row.get('Role') or '').strip()

                # Basic validation
                if not (email and mobile and full_name and gender and role_name):
                    self.stdout.write(self.style.WARNING(
                        f"Row {row_num}: Missing required field(s): {row}"
                    ))
                    continue

                # Role creation
                role, role_created = Role.objects.get_or_create(name=role_name)
                if role_created:
                    created_roles += 1
                    self.stdout.write(self.style.SUCCESS(f"Created new role: {role_name}"))

                # Check if a user with the same mobile already exists
                user_by_mobile = User.objects.filter(mobile=mobile).first()
                user_by_email = User.objects.filter(email=email).first()

                if user_by_mobile and user_by_mobile.email != email:
                    skipped_conflicts += 1
                    self.stdout.write(self.style.WARNING(
                        f"Row {row_num}: Mobile number {mobile} already exists with a different email ({user_by_mobile.email}). Skipping row."
                    ))
                    continue

                user = user_by_email or user_by_mobile

                try:
                    if user:
                        # Update existing user
                        user.email = email
                        user.mobile = mobile
                        user.full_name = full_name
                        user.gender = gender
                        user.organization = organization
                        user.is_active = True
                        user.set_password(DEFAULT_PASSWORD)
                        user.save()
                        updated_users += 1
                        self.stdout.write(self.style.WARNING(f"Updated user: {email}"))
                    else:
                        # Create new user
                        user = User.objects.create(
                            email=email,
                            mobile=mobile,
                            full_name=full_name,
                            gender=gender,
                            organization=organization,
                            is_active=True
                        )
                        user.set_password(DEFAULT_PASSWORD)
                        user.save()
                        created_users += 1
                        self.stdout.write(self.style.SUCCESS(f"Created user: {email}"))

                    # Assign role
                    if not user.roles.filter(pk=role.pk).exists():
                        user.roles.add(role)
                        self.stdout.write(self.style.SUCCESS(
                            f"Assigned role '{role_name}' to user {email}"
                        ))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: Error processing user {email or mobile} - {str(e)}"
                    ))
                    continue

        self.stdout.write(self.style.SUCCESS(
            f"\nImport Summary:\n"
            f"Users created: {created_users}\n"
            f"Users updated: {updated_users}\n"
            f"Roles created: {created_roles}\n"
            f"Rows skipped due to mobile/email conflict: {skipped_conflicts}"
        ))
