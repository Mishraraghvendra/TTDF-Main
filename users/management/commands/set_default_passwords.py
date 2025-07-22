from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Set a default password for all users (NAME in caps + last 4 of mobile, else Test@1234), with summary counts."

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()

        total_set = 0
        total_not_set = 0
        total_test1234 = 0

        for user in users:
            try:
                name_clean = user.full_name.replace(" ", "") if user.full_name else ""
                has_name = len(name_clean) >= 4
                has_mobile = user.mobile and len(user.mobile) >= 4

                if has_name and has_mobile:
                    name_part = name_clean[:4].upper()
                    mobile_part = user.mobile[-4:]
                    default_password = f"{name_part}{mobile_part}"
                else:
                    default_password = "Test@1234"
                    total_test1234 += 1

                user.set_password(default_password)
                user.save(update_fields=["password"])
                total_set += 1
                self.stdout.write(f"User: {user.email}, Password set: {default_password}")

            except Exception as e:
                total_not_set += 1
                self.stdout.write(self.style.ERROR(f"User: {getattr(user, 'email', user.pk)}: ERROR: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nSummary:"))
        self.stdout.write(self.style.SUCCESS(f"Total passwords set: {total_set}"))
        self.stdout.write(self.style.SUCCESS(f"Total passwords NOT set: {total_not_set}"))
        self.stdout.write(self.style.WARNING(f"Total passwords set to Test@1234: {total_test1234}"))
