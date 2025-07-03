import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

from dynamic_form.models import FormSubmission
from app_eval.models import EvaluationItem, EvaluationAssignment  # Your models

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
        # Try a few common formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return timezone.make_aware(
                    timezone.datetime.strptime(val.strip(), fmt)
                )
            except Exception:
                continue
        return None
    except Exception:
        return None

class Command(BaseCommand):
    help = 'Import EvaluationItem criteria and EvaluationAssignment from CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to your CSV file')

    def handle(self, *args, **options):
        csv_path = options['csv_path']

        with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, start=2):
                # --- EVALUATION ITEM (CRITERIA) ---
                criteria_key   = row.get('key', '').strip()
                criteria_name  = row.get('name', '').strip()
                description    = row.get('Description', '').strip()
                total_marks    = clean_decimal(row.get('total_marks'))
                weightage      = clean_decimal(row.get('weightage'))
                # Optionally you can add: status/type/memberType/created_by etc

                if not criteria_key or not criteria_name:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: Missing 'key' or 'name' for EvaluationItem."
                    ))
                    continue
                if total_marks is None:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: Missing 'total_marks' for criteria '{criteria_name}'."
                    ))
                    continue

                eval_item, created = EvaluationItem.objects.get_or_create(
                    key=criteria_key,
                    defaults={
                        'name': criteria_name,
                        'description': description,
                        'total_marks': total_marks,
                        'weightage': weightage or 0,
                        'status': 'Active',
                        'type': 'criteria',
                        'memberType': 'General',
                        'created_by': None,  # Set to a user if desired
                    }
                )
                if not created:
                    # Update fields if necessary
                    updated = False
                    if eval_item.name != criteria_name:
                        eval_item.name = criteria_name
                        updated = True
                    if eval_item.description != description:
                        eval_item.description = description
                        updated = True
                    if eval_item.total_marks != total_marks:
                        eval_item.total_marks = total_marks
                        updated = True
                    if eval_item.weightage != (weightage or 0):
                        eval_item.weightage = weightage or 0
                        updated = True
                    if updated:
                        eval_item.save()
                        self.stdout.write(self.style.SUCCESS(
                            f"Row {row_num}: Updated EvaluationItem key={criteria_key}."
                        ))
                    else:
                        self.stdout.write(
                            f"Row {row_num}: Existing EvaluationItem key={criteria_key}."
                        )
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f"Row {row_num}: Created EvaluationItem key={criteria_key}."
                    ))

                # --- EVALUATION ASSIGNMENT ---
                proposal_id = row.get('ID', '').strip()
                evaluator_email = row.get('evaluator', '').strip()
                total_marks_assigned = clean_decimal(row.get('total_marks_assigned'))
                evaluated_at = parse_datetime(row.get('evaluated_at'))
                remarks = row.get('remarks', '').strip()

                if not proposal_id or not evaluator_email:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: Missing 'ID' (proposal) or 'evaluator' (email) for EvaluationAssignment."
                    ))
                    continue

                try:
                    form_submission = FormSubmission.objects.get(proposal_id=proposal_id)
                except FormSubmission.DoesNotExist:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: Proposal with ID {proposal_id} not found."
                    ))
                    continue

                try:
                    evaluator = User.objects.get(email=evaluator_email)
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: Evaluator {evaluator_email} not found."
                    ))
                    continue

                eval_assign, assign_created = EvaluationAssignment.objects.get_or_create(
                    form_submission=form_submission,
                    evaluator=evaluator,
                    defaults={
                        'total_marks_assigned': total_marks_assigned,
                        'evaluated_at': evaluated_at,
                        'remarks': remarks,
                        'is_completed': True if evaluated_at else False,
                    }
                )
                if not assign_created:
                    updated = False
                    if eval_assign.total_marks_assigned != total_marks_assigned:
                        eval_assign.total_marks_assigned = total_marks_assigned
                        updated = True
                    if eval_assign.evaluated_at != evaluated_at and evaluated_at:
                        eval_assign.evaluated_at = evaluated_at
                        updated = True
                    if eval_assign.remarks != remarks:
                        eval_assign.remarks = remarks
                        updated = True
                    # Optionally set is_completed if marks/evaluated_at
                    if evaluated_at and not eval_assign.is_completed:
                        eval_assign.is_completed = True
                        updated = True
                    if updated:
                        eval_assign.save()
                        self.stdout.write(self.style.SUCCESS(
                            f"Row {row_num}: Updated EvaluationAssignment for {proposal_id}, evaluator {evaluator_email}."
                        ))
                    else:
                        self.stdout.write(
                            f"Row {row_num}: Existing EvaluationAssignment for {proposal_id}, evaluator {evaluator_email}."
                        )
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f"Row {row_num}: Created EvaluationAssignment for {proposal_id}, evaluator {evaluator_email}."
                    ))
