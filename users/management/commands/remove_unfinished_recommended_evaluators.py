from django.core.management.base import BaseCommand
from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment  # Adjust import paths

class Command(BaseCommand):
    help = "Update assignment_status to completed where all assignments are completed, and remove incomplete evaluators from recommended rounds"

    def handle(self, *args, **options):
        # 1. Set assignment_status = 'completed' where all assignments are completed
        rounds = TechnicalEvaluationRound.objects.all()
        updated_completed = 0

        for round in rounds:
            # Check if all assignments are completed and there is at least one assignment
            assignments = round.evaluator_assignments.all()
            total = assignments.count()
            completed = assignments.filter(is_completed=True).count()

            if total > 0 and total == completed and round.assignment_status != 'completed':
                round.assignment_status = 'completed'
                round.save()
                updated_completed += 1

        self.stdout.write(f"Updated {updated_completed} rounds to assignment_status = 'completed'")

        # 2. Remove evaluators from recommended rounds where assignment is not completed
        recommended_rounds = TechnicalEvaluationRound.objects.filter(overall_decision='recommended')
        removed_count = 0

        for round in recommended_rounds:
            incomplete_assignments = round.evaluator_assignments.filter(is_completed=False)
            removed = incomplete_assignments.count()
            if removed > 0:
                incomplete_assignments.delete()
                removed_count += removed

        self.stdout.write(f"Removed {removed_count} incomplete evaluator assignments from recommended rounds.")
