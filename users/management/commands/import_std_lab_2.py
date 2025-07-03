import csv
import datetime
import uuid

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

def normalize_header(header):
    return header.strip().lower().replace(' ', '_').replace('\ufeff', '')

class Command(BaseCommand):
    help = 'Import milestones and presentations from CSV by proposal_id and update TechnicalEvaluationRound'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file to import')

    def handle(self, *args, **options):
        from milestones.models import Milestone
        from presentation.models import Presentation
        from dynamic_form.models import FormSubmission
        from tech_eval.models import TechnicalEvaluationRound  # Your model

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

            for row in reader:
                proposal_id = val(row, 'proposal_id') or val(row, 'id') or val(row, 'Proposal ID')
                if not proposal_id:
                    self.stdout.write(self.style.WARNING("Skipping row: no proposal_id found"))
                    continue

                # --- Find proposal ---
                try:
                    proposal = FormSubmission.objects.get(proposal_id=proposal_id)
                except FormSubmission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"No proposal found for proposal_id {proposal_id}"))
                    continue

                # --- Create/update Milestone ---
                milestone, ms_created = Milestone.objects.update_or_create(
                    proposal=proposal,
                    defaults={
                        'title': val(row, 'title') or f'Milestone for {proposal_id}',
                        'description': val(row, 'description', ''),
                        'time_required': val_int(row, 'time_required', 1),
                        'revised_time_required': val_int(row, 'revised_time_required', 1),
                        'funds_requested': val_int(row, 'funds_requested', 0),
                        'grant_from_ttdf': val_int(row, 'grant_from_ttdf', 0),
                        'initial_contri_applicant': val_int(row, 'initial_contri_applicant', 0),
                        'revised_contri_applicant': val_int(row, 'revised_contri_applicant', 0),
                        'initial_grant_from_ttdf': val_int(row, 'initial_grant_from_ttdf', 0),
                        'revised_grant_from_ttdf': val_int(row, 'revised_grant_from_ttdf', 0),
                        'created_by': proposal.applicant,
                        'updated_by': proposal.applicant,
                        # agreement and mou_document skipped (handle files separately)
                    }
                )
                self.stdout.write(self.style.SUCCESS(
                    f"{'Created' if ms_created else 'Updated'} Milestone for proposal {proposal_id}"
                ))

                # --- Create/update Presentation ---
                video_link = val(row, 'video_link', None) or None
                presentation, pres_created = Presentation.objects.update_or_create(
                    proposal=proposal,
                    applicant=proposal.applicant,
                    defaults={
                        'video_link': video_link,
                        # You may map more fields here from your CSV if desired
                        # 'presentation_date': ...,
                        # 'final_decision': ...,
                        # 'document_uploaded': ...,
                    }
                )
                self.stdout.write(self.style.SUCCESS(
                    f"{'Created' if pres_created else 'Updated'} Presentation for proposal {proposal_id}"
                ))

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
                    self.stdout.write(self.style.SUCCESS(
                        f"Updated TechnicalEvaluationRound for {proposal_id}: overall_decision={overall_decision}, assignment_status={assignment_status}"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"No TechnicalEvaluationRound found for proposal {proposal_id}, skipping updates."
                    ))
