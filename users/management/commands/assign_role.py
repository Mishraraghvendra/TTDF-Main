from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Role  # Update this import path as needed

class Command(BaseCommand):
    help = "Assign the 'User' role to all users who do not have any roles assigned."

    def handle(self, *args, **options):
        User = get_user_model()
        role_name = "User"  # Hardcoded role

        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Role '{role_name}' does not exist!"))
            return

        users_without_roles = User.objects.filter(roles=None)
        count = 0
        for user in users_without_roles:
            user.roles.add(role)
            count += 1
            self.stdout.write(f"Assigned '{role_name}' role to {user.email}")

        self.stdout.write(self.style.SUCCESS(f"Total users assigned role '{role_name}': {count}"))
