import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from dynamic_form.models import FormSubmission
from app_eval.models import EvaluationItem
from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment, CriteriaEvaluation

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
    help = 'Import EvaluationItem criteria, EvaluatorAssignment, and CriteriaEvaluation from CSV'

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
                        'created_by': None,
                    }
                )
                if not created:
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

                # --- EVALUATOR ASSIGNMENT ---
                proposal_id = row.get('ID', '').strip()
                evaluator_email = row.get('evaluator', '').strip()
                remarks = row.get('remarks', '').strip()
                evaluated_at = parse_datetime(row.get('evaluated_at'))

                if not proposal_id or not evaluator_email:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: Missing 'ID' (proposal) or 'evaluator' (email) for EvaluatorAssignment."
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
                    eval_round = TechnicalEvaluationRound.objects.get(proposal=form_submission)
                except TechnicalEvaluationRound.DoesNotExist:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: TechnicalEvaluationRound for proposal {proposal_id} not found."
                    ))
                    continue

                try:
                    evaluator = User.objects.get(email=evaluator_email)
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: Evaluator {evaluator_email} not found."
                    ))
                    continue

                eval_assign, assign_created = EvaluatorAssignment.objects.get_or_create(
                    evaluation_round=eval_round,
                    evaluator=evaluator,
                    defaults={
                        'overall_comments': remarks,
                        'is_completed': True if evaluated_at else False,
                        'completed_at': evaluated_at if evaluated_at else None,
                    }
                )
                updated = False
                if not assign_created:
                    if eval_assign.overall_comments != remarks:
                        eval_assign.overall_comments = remarks
                        updated = True
                    if evaluated_at and eval_assign.completed_at != evaluated_at:
                        eval_assign.completed_at = evaluated_at
                        updated = True
                    if evaluated_at and not eval_assign.is_completed:
                        eval_assign.is_completed = True
                        updated = True
                    if updated:
                        eval_assign.save()
                        self.stdout.write(self.style.SUCCESS(
                            f"Row {row_num}: Updated EvaluatorAssignment for proposal {proposal_id}, evaluator {evaluator_email}."
                        ))
                    else:
                        self.stdout.write(
                            f"Row {row_num}: Existing EvaluatorAssignment for proposal {proposal_id}, evaluator {evaluator_email}."
                        )
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f"Row {row_num}: Created EvaluatorAssignment for proposal {proposal_id}, evaluator {evaluator_email}."
                    ))

                # --- CRITERIA EVALUATION ---
                marks_given = clean_decimal(row.get('Marks given'))
                crit_remarks = row.get('remarks', '').strip()
                crit_eval_at = parse_datetime(row.get('evaluated_at'))

                if marks_given is None:
                    self.stdout.write(self.style.WARNING(
                        f"Row {row_num}: No marks for criteria {criteria_name}, skipping CriteriaEvaluation for proposal {proposal_id}, evaluator {evaluator_email}."
                    ))
                    continue

                try:
                    crit_eval, ce_created = CriteriaEvaluation.objects.get_or_create(
                        evaluator_assignment=eval_assign,
                        evaluation_criteria=eval_item,
                        defaults={
                            'marks_given': marks_given,
                            'remarks': crit_remarks,
                            'evaluated_at': crit_eval_at or timezone.now(),
                        }
                    )
                    updated = False
                    if not ce_created:
                        if crit_eval.marks_given != marks_given:
                            crit_eval.marks_given = marks_given
                            updated = True
                        if crit_eval.remarks != crit_remarks:
                            crit_eval.remarks = crit_remarks
                            updated = True
                        if crit_eval_at and crit_eval.evaluated_at != crit_eval_at:
                            crit_eval.evaluated_at = crit_eval_at
                            updated = True
                        if updated:
                            crit_eval.save()
                    self.stdout.write(self.style.SUCCESS(
                        f"Row {row_num}: {'Created' if ce_created else 'Updated'} CriteriaEvaluation for proposal {proposal_id}, evaluator {evaluator_email}, criteria '{criteria_name}' (marks={marks_given}, remarks={crit_remarks})"
                    ))
                except Exception as ex:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: Could not save CriteriaEvaluation for proposal {proposal_id}, evaluator {evaluator_email}, criteria '{criteria_name}'. Error: {ex}"
                    ))
