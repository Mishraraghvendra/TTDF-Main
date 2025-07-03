import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Role  # Update if Role is in a different app

User = get_user_model()

class Command(BaseCommand):
    help = "Import users and roles from UserStdlabP.csv; set default password; create missing roles; set user flags"

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to UserStdlabP.csv')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        created_count = 0
        updated_count = 0
        role_created_count = 0
        role_assigned_count = 0

        with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            print("CSV headers:", reader.fieldnames)
            for row in reader:
                email = row.get('email')
                full_name = row.get('full_name') or row.get('name')
                mobile = row.get('mobile')
                gender = row.get('gender', 'O')
                organization = row.get('organization', '')
                role_name = (row.get('role') or row.get('Role') or '').strip()

                # Boolean fields (default to True or False as needed)
                is_staff = row.get('is_staff', 'False').strip().lower() in ('true', '1', 'yes')
                is_applicant = row.get('is_applicant', 'True').strip().lower() in ('true', '1', 'yes')
                is_auth_user = row.get('is_auth_user', 'False').strip().lower() in ('true', '1', 'yes')

                if not email or not mobile or not full_name:
                    print(f"Skipping: missing required fields in row: {row}")
                    continue

                # Create or get the role
                role = None
                if role_name:
                    role, role_created = Role.objects.get_or_create(name=role_name)
                    if role_created:
                        role_created_count += 1
                        print(f"Created Role: {role_name}")

                # Create or get the user
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'full_name': full_name,
                        'mobile': mobile,
                        'gender': gender,
                        'organization': organization,
                        'is_active': True,
                        'is_staff': is_staff,
                        'is_applicant': is_applicant,
                        'is_auth_user': is_auth_user,
                    }
                )

                needs_update = False

                # Set fields for existing users, or update if they have changed
                for field, val in [
                    ('full_name', full_name),
                    ('mobile', mobile),
                    ('gender', gender),
                    ('organization', organization),
                    ('is_active', True),
                    ('is_staff', is_staff),
                    ('is_applicant', is_applicant),
                    ('is_auth_user', is_auth_user),
                ]:
                    if getattr(user, field, None) != val:
                        setattr(user, field, val)
                        needs_update = True

                if created:
                    user.set_password('Test@1234')
                    needs_update = True

                if needs_update:
                    user.save()
                    msg = "Created" if created else "Updated"
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                else:
                    msg = "Exists (no change)"

                # Assign role if found or created
                if role:
                    if not user.roles.filter(id=role.id).exists():
                        user.roles.add(role)
                        role_assigned_count += 1
                        print(f"Assigned role '{role.name}' to {user.email}")

                print(f"{msg}: {email} ({full_name})")

        print(
            f"\nSummary: Created users: {created_count}, Updated users: {updated_count}, "
            f"Created roles: {role_created_count}, Roles assigned: {role_assigned_count}"
        )
