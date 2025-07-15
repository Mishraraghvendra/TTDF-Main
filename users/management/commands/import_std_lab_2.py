import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

def normalize_header(header):
    return header.strip().lower().replace(' ', '_').replace('\ufeff', '')

class Command(BaseCommand):
    help = 'Update funds_requested on FormSubmission and related info from CSV (NO Milestone creation).'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file to import')

    def handle(self, *args, **options):
        # Only import models you actually use now:
        from presentation.models import Presentation
        from dynamic_form.models import FormSubmission
        from tech_eval.models import TechnicalEvaluationRound

        csv_path = options['csv_path']
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            header_map = {normalize_header(col): col for col in reader.fieldnames}

            def val(row, name, default=''):
                raw = row.get(header_map.get(normalize_header(name)), default)
                if raw is None:
                    return default
                return str(raw).strip()

            def val_int(row, name, default=0):
                try:
                    return int(float(val(row, name, default)))
                except (ValueError, TypeError):
                    return default

            for idx, row in enumerate(reader, start=1):
                proposal_id = val(row, 'ID') or val(row, 'proposal_id') or val(row, 'id') or val(row, 'Proposal ID')
                if not proposal_id:
                    print(f"[Row {idx}] Skipping: no proposal_id found")
                    continue

                try:
                    proposal = FormSubmission.objects.get(proposal_id=proposal_id)
                except FormSubmission.DoesNotExist:
                    print(f"[Row {idx}] No proposal found for proposal_id {proposal_id}")
                    continue

                # --- Set funds_requested on FormSubmission ---
                csv_funds_requested = val_int(row, 'Funds Requested', 0)
                print(f"[Row {idx}] Proposal {proposal_id}: funds_requested BEFORE = {proposal.funds_requested}, CSV = {csv_funds_requested}")
                proposal.funds_requested = csv_funds_requested
                proposal.save(update_fields=['funds_requested'])
                proposal.refresh_from_db()
                print(f"[Row {idx}] Proposal {proposal_id}: funds_requested AFTER = {proposal.funds_requested}")

                # --- (optional) Create/update Presentation ---
                video_link = val(row, 'Video Link', None) or None
                presentation, pres_created = Presentation.objects.update_or_create(
                    proposal=proposal,
                    applicant=proposal.applicant,
                    defaults={
                        'video_link': video_link,
                        # Map more fields as needed
                    }
                )
                print(f"[Row {idx}] {'Created' if pres_created else 'Updated'} Presentation for {proposal_id}.")

                # --- Update TechnicalEvaluationRound.overall_decision and assignment_status ---
                try:
                    tech_eval_round = TechnicalEvaluationRound.objects.get(proposal=proposal)
                except TechnicalEvaluationRound.DoesNotExist:
                    tech_eval_round = None

                shortlisted_raw = val(row, 'Shortlisted', '').strip()
                if shortlisted_raw == '1':
                    overall_decision = 'recommended'
                    assignment_status = 'completed'
                elif shortlisted_raw == '0':
                    overall_decision = 'not_recommended'
                    assignment_status = 'completed'
                else:
                    overall_decision = 'pending'
                    assignment_status = 'pending'

                if tech_eval_round:
                    tech_eval_round.overall_decision = overall_decision
                    tech_eval_round.assignment_status = assignment_status
                    tech_eval_round.save()
                    print(f"[Row {idx}] Updated TechnicalEvaluationRound for {proposal_id}: overall_decision={overall_decision}, assignment_status={assignment_status}")
                else:
                    print(f"[Row {idx}] No TechnicalEvaluationRound found for proposal {proposal_id}, skipping updates.")

        print("Import completed!")
