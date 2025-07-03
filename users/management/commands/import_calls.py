import csv
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from configuration.models import Service  # Adjust import as per your app

User = get_user_model()

def parse_datetime_or_none(val):
    if not val or val.strip() == '':
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return timezone.make_aware(datetime.datetime.strptime(val.strip(), fmt))
        except Exception:
            continue
    return None

def to_bool(val):
    if isinstance(val, bool):
        return val
    v = str(val).strip().lower()
    if v in ('1', 'true', 'yes'):
        return True
    if v in ('0', 'false', 'no'):
        return False
    return False

class Command(BaseCommand):
    help = "Import or update Service records from CSV using only the 'name' field."

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to calls.csv')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            self.stdout.write(self.style.WARNING(f"Detected CSV headers: {reader.fieldnames}"))
            for row_num, row in enumerate(reader, start=2):
                name = (row.get('name') or '').strip()
                if not name:
                    self.stdout.write(self.style.ERROR(f"[Row {row_num}] Skipped: Blank 'name' field"))
                    continue

                description = (row.get('description') or '').strip()
                status = (row.get('status') or 'draft').strip()
                is_active = to_bool(row.get('is_active', True))
                start_date = parse_datetime_or_none(row.get('start_date', '').strip())
                end_date = parse_datetime_or_none(row.get('end_date', '').strip())
                created_by_email = (row.get('created_by') or '').strip()
                created_by = None
                if created_by_email:
                    created_by = User.objects.filter(email=created_by_email).first()

                service, created = Service.objects.get_or_create(name=name)
                # Always update all fields (even after create)
                service.description = description
                service.status = status
                service.is_active = is_active
                service.start_date = start_date
                service.end_date = end_date
                if created_by:
                    service.created_by = created_by
                service.save()
                self.stdout.write(self.style.SUCCESS(
                    f"[Row {row_num}] {'Created' if created else 'Updated'} Service '{name}'"
                ))
        self.stdout.write(self.style.SUCCESS("Service import/update completed!"))
