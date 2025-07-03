import csv
import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from dynamic_form.models import FormSubmission
from presentation.models import Presentation

User = get_user_model()

def clean_decimal(val):
    try:
        if val is None or str(val).strip() == "":
            return None
        return Decimal(str(val).strip())
    except InvalidOperation:
        return None

def parse_datetime(val):
    try:
        if not val or val.strip() == "":
            return None
        for fmt in ("%d-%m-%Y %H:%M", "%d-%m-%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.datetime.strptime(val.strip(), fmt)
                return timezone.make_aware(dt)
            except Exception:
                continue
        return None
    except Exception:
        return None

class Command(BaseCommand):
    help = "Import/update Presentation from CSV: evaluator_remarks, evaluated_at, final_decision, document_uploaded, etc."

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to Presentation CSV')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            self.stdout.write(self.style.WARNING(f"Detected CSV headers: {reader.fieldnames}"))

            for row_num, row in enumerate(reader, start=2):
                proposal_id = row.get('ID', '').strip()
                evaluator_email = row.get('Evaluator', '').strip()
                marks_str = row.get('Marks', '').strip()
                eval_remarks = row.get('evaluator_remarks', '').strip()
                eval_date_str = row.get('Date', '').strip()
                video_link = row.get('Video Link', '').strip()
                sortlisted = row.get('Sortlisted', '').strip().lower()

                if not proposal_id:
                    self.stdout.write(self.style.ERROR(f"[Row {row_num}] Proposal ID missing. Skipping."))
                    continue

                # --- Get Proposal ---
                try:
                    proposal = FormSubmission.objects.get(proposal_id=proposal_id)
                except FormSubmission.DoesNotExist:
                    self.stdout.write(self.style.ERROR(
                        f"[Row {row_num}] Proposal ID {proposal_id} not found. Skipping."
                    ))
                    continue

                # --- Get Evaluator User ---
                evaluator_user = None
                if evaluator_email:
                    try:
                        evaluator_user = User.objects.get(email=evaluator_email)
                    except User.DoesNotExist:
                        self.stdout.write(self.style.WARNING(
                            f"[Row {row_num}] Evaluator '{evaluator_email}' not found. Presentation will be created without evaluator."
                        ))

                applicant = proposal.applicant

                # --- Parse Fields ---
                marks = clean_decimal(marks_str)
                evaluated_at = parse_datetime(eval_date_str) if marks is not None else None

                # --- Decision Logic ---
                if marks is not None:
                    if sortlisted == 'yes':
                        final_decision = 'shortlisted'
                    elif sortlisted == 'no':
                        final_decision = 'rejected'
                    else:
                        final_decision = 'evaluated'
                else:
                    final_decision = 'pending'

                document_uploaded = bool(video_link)
                admin_evaluated_at = None
                if final_decision in ['shortlisted', 'rejected']:
                    admin_evaluated_at = timezone.now()

                pres, created = Presentation.objects.get_or_create(
                    proposal=proposal,
                    applicant=applicant,
                    evaluator=evaluator_user,
                    defaults={
                        'evaluator_marks': marks,
                        'evaluator_remarks': eval_remarks,
                        'evaluated_at': evaluated_at,
                        'video_link': video_link if video_link else None,
                        'presentation_date': evaluated_at,
                    }
                )

                # --- Always Update All Key Fields ---
                pres.evaluator_marks = marks
                pres.evaluator_remarks = eval_remarks
                pres.evaluated_at = evaluated_at
                pres.video_link = video_link if video_link else None
                pres.presentation_date = evaluated_at

                # Compose list of update_fields (no None values)
                fields_to_update = [
                    'evaluator_marks',
                    'evaluator_remarks',
                    'evaluated_at',
                    'video_link',
                    'presentation_date', 
                    'document_uploaded',
                    'final_decision',
                ]
                if admin_evaluated_at:
                    pres.admin_evaluated_at = admin_evaluated_at
                    fields_to_update.append('admin_evaluated_at')

                pres.document_uploaded = document_uploaded
                pres.final_decision = final_decision

                pres.save(update_fields=fields_to_update)

                self.stdout.write(self.style.SUCCESS(
                    f"[Row {row_num}] {'Created' if created else 'Updated'} Presentation for proposal {proposal_id}, applicant {applicant.email} (document_uploaded={document_uploaded}, final_decision={final_decision})"
                ))

        self.stdout.write(self.style.SUCCESS("Presentation import completed!"))
