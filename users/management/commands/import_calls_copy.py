import csv
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from configuration.models import Service

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
    help = "Import/update Service records from CSV (supports renaming via 'Old name')."

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to calls.csv')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            self.stdout.write(self.style.WARNING(f"Detected CSV headers: {reader.fieldnames}"))
            for row_num, row in enumerate(reader, start=2):
                old_name = (row.get('Old name') or '').strip()
                name = (row.get('name') or '').strip()
                start_date = parse_datetime_or_none(row.get('start_date', '').strip())
                end_date = parse_datetime_or_none(row.get('end_date', '').strip())
                status = (row.get('status') or 'draft').strip()
                description = (row.get('description') or '').strip()
                is_active = to_bool(row.get('is_active', True))
                created_by_email = (row.get('created_by') or '').strip()
                created_by = None
                if created_by_email:
                    created_by = User.objects.filter(email=created_by_email).first()

                # If no name, skip row
                if not name:
                    self.stdout.write(self.style.ERROR(f"[Row {row_num}] Skipped: Blank 'name' field"))
                    continue

                # Update by old_name if present and found
                if old_name:
                    service = Service.objects.filter(name=old_name).first()
                    if service:
                        changed = False
                        if service.name != name:
                            service.name = name
                            changed = True
                        if service.description != description:
                            service.description = description
                            changed = True
                        if service.status != status:
                            service.status = status
                            changed = True
                        if service.is_active != is_active:
                            service.is_active = is_active
                            changed = True
                        # Always update dates (clear if empty)
                        if service.start_date != start_date:
                            service.start_date = start_date
                            changed = True
                        if service.end_date != end_date:
                            service.end_date = end_date
                            changed = True
                        if created_by and service.created_by != created_by:
                            service.created_by = created_by
                            changed = True
                        if changed:
                            service.save()
                            self.stdout.write(self.style.SUCCESS(
                                f"[Row {row_num}] Updated existing Service '{old_name}' to '{service.name}'"
                            ))
                        else:
                            self.stdout.write(
                                f"[Row {row_num}] No change needed for Service '{old_name}'"
                            )
                        continue  # Next row

                # Otherwise, update by name or create if not found
                service, created = Service.objects.get_or_create(
                    name=name,
                    defaults={
                        'description': description,
                        'status': status,
                        'is_active': is_active,
                        'start_date': start_date,
                        'end_date': end_date,
                        'created_by': created_by,
                    }
                )
                if not created:
                    changed = False
                    if service.description != description:
                        service.description = description
                        changed = True
                    if service.status != status:
                        service.status = status
                        changed = True
                    if service.is_active != is_active:
                        service.is_active = is_active
                        changed = True
                    # Always update dates (clear if empty)
                    if service.start_date != start_date:
                        service.start_date = start_date
                        changed = True
                    if service.end_date != end_date:
                        service.end_date = end_date
                        changed = True
                    if created_by and service.created_by != created_by:
                        service.created_by = created_by
                        changed = True
                    if changed:
                        service.save()
                        self.stdout.write(self.style.SUCCESS(
                            f"[Row {row_num}] Updated existing Service '{name}'"
                        ))
                    else:
                        self.stdout.write(
                            f"[Row {row_num}] No change needed for Service '{name}'"
                        )
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f"[Row {row_num}] Created Service '{name}'"
                    ))

        self.stdout.write(self.style.SUCCESS("Service import/update completed!"))
