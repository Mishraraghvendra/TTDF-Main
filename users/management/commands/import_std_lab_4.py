import csv
import re
import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

def extract_emails(evaluator_str):
    # Matches patterns like: "Name (email@domain)" or just "email@domain"
    return re.findall(r'[\w\.-]+@[\w\.-]+', evaluator_str or "")

class Command(BaseCommand):
    help = 'Import evaluator assignments proposal-wise (multi-evaluator) from CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file to import')

    def handle(self, *args, **options):
        from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment
        from dynamic_form.models import FormSubmission

        csv_path = options['csv_path']
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            print("DETECTED HEADERS:", reader.fieldnames)
            for row in reader:
                proposal_id = row.get('\ufeffID') or row.get('ID')
                evaluators_raw = row.get('Assigned Evaluator')

                if not proposal_id or not evaluators_raw:
                    self.stdout.write(self.style.WARNING(
                        f"Skipping row: Missing proposal_id or evaluator list -- Detected: {proposal_id}, {evaluators_raw}"
                    ))
                    continue

                try:
                    proposal = FormSubmission.objects.get(proposal_id=proposal_id)
                except FormSubmission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Proposal not found: {proposal_id}"))
                    continue

                emails = extract_emails(evaluators_raw)
                if not emails:
                    self.stdout.write(self.style.WARNING(f"No valid evaluator emails found for proposal {proposal_id}"))
                    continue

                # Ensure TechnicalEvaluationRound exists
                tech_eval_round, _ = TechnicalEvaluationRound.objects.get_or_create(proposal=proposal)
                assigned = 0

                for email in emails:
                    evaluator = User.objects.filter(email__iexact=email).first()
                    if not evaluator:
                        # Auto-create minimal user if missing
                        evaluator = User.objects.create(
                            email=email,
                            mobile=f"99999{str(uuid.uuid4())[:5]}",
                            full_name=email.split('@')[0],
                            gender='O',
                            is_active=True
                        )
                        self.stdout.write(self.style.WARNING(f"Auto-created evaluator: {email}"))

                    assignment, created = EvaluatorAssignment.objects.get_or_create(
                        evaluation_round=tech_eval_round,
                        evaluator=evaluator,
                    )
                    assigned += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"{'Created' if created else 'Exists'}: {proposal_id} ← {email}"
                    ))

                if not assigned:
                    self.stdout.write(self.style.WARNING(f"No assignments created for {proposal_id}"))

