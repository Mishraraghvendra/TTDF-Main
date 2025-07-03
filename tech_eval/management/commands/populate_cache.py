# tech_eval/management/commands/populate_cache.py

from django.core.management.base import BaseCommand
from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment, CriteriaEvaluation

class Command(BaseCommand):
    help = 'Populate cached values for tech_eval models'
    
    def handle(self, *args, **options):
        self.stdout.write("Starting cache population...")
        
        # Update criteria evaluations
        criteria_count = 0
        for ce in CriteriaEvaluation.objects.all():
            try:
                if ce.evaluation_criteria and ce.evaluation_criteria.total_marks:
                    total_marks = float(ce.evaluation_criteria.total_marks)
                    if total_marks > 0:
                        percentage = round((float(ce.marks_given) / total_marks) * 100, 2)
                        ce.cached_percentage = percentage
                        ce.cached_weighted_score = percentage
                        ce.save(update_fields=['cached_percentage', 'cached_weighted_score'])
                        criteria_count += 1
            except Exception as e:
                self.stdout.write(f"Error updating criteria {ce.id}: {e}")
        
        self.stdout.write(f"Updated {criteria_count} criteria evaluations")
        
        # Update assignments
        assignment_count = 0
        for assignment in EvaluatorAssignment.objects.filter(is_completed=True):
            try:
                criteria_evaluations = assignment.criteria_evaluations.all()
                if criteria_evaluations.exists():
                    raw_total = sum(float(ce.marks_given) for ce in criteria_evaluations)
                    max_total = sum(float(ce.evaluation_criteria.total_marks) 
                                  for ce in criteria_evaluations 
                                  if ce.evaluation_criteria and ce.evaluation_criteria.total_marks)
                    
                    if max_total > 0:
                        percentage = round((raw_total / max_total) * 100, 2)
                        assignment.cached_raw_marks = raw_total
                        assignment.cached_max_marks = max_total
                        assignment.cached_percentage_score = percentage
                        assignment.cached_criteria_count = criteria_evaluations.count()
                        assignment.save(update_fields=[
                            'cached_raw_marks', 'cached_max_marks', 
                            'cached_percentage_score', 'cached_criteria_count'
                        ])
                        assignment_count += 1
            except Exception as e:
                self.stdout.write(f"Error updating assignment {assignment.id}: {e}")
        
        self.stdout.write(f"Updated {assignment_count} assignments")
        
        # Update evaluation rounds
        round_count = 0
        for eval_round in TechnicalEvaluationRound.objects.all():
            try:
                assigned_count = eval_round.evaluator_assignments.count()
                completed_count = eval_round.evaluator_assignments.filter(is_completed=True).count()
                
                # Calculate average
                completed_assignments = eval_round.evaluator_assignments.filter(
                    is_completed=True,
                    cached_percentage_score__isnull=False
                )
                
                if completed_assignments.exists():
                    total_score = sum(a.cached_percentage_score for a in completed_assignments)
                    avg_percentage = round(total_score / completed_assignments.count(), 2)
                else:
                    avg_percentage = None
                
                eval_round.cached_assigned_count = assigned_count
                eval_round.cached_completed_count = completed_count
                eval_round.cached_average_percentage = avg_percentage
                eval_round.save(update_fields=[
                    'cached_assigned_count', 'cached_completed_count', 'cached_average_percentage'
                ])
                round_count += 1
                
            except Exception as e:
                self.stdout.write(f"Error updating round {eval_round.id}: {e}")
        
        self.stdout.write(f"Updated {round_count} evaluation rounds")
        self.stdout.write(self.style.SUCCESS("Cache population completed!"))