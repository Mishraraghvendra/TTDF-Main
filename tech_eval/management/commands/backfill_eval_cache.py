from django.core.management.base import BaseCommand
from tech_eval.models import (
    TechnicalEvaluationRound, 
    EvaluatorAssignment, 
    CriteriaEvaluation,
)
from tqdm import tqdm  # Optional: for progress bar, `pip install tqdm`

class Command(BaseCommand):
    help = "Backfill all cached fields for TechnicalEvaluationRound, EvaluatorAssignment, and CriteriaEvaluation"

    def handle(self, *args, **options):
        # 1. Backfill CriteriaEvaluation (lowest level)
        self.stdout.write(self.style.WARNING("Updating CriteriaEvaluations..."))
        criteria_qs = CriteriaEvaluation.objects.all()
        for ce in tqdm(criteria_qs, desc="CriteriaEvaluations"):
            ce.update_cached_values()

        # 2. Backfill EvaluatorAssignment
        self.stdout.write(self.style.WARNING("Updating EvaluatorAssignments..."))
        assignment_qs = EvaluatorAssignment.objects.all()
        for ea in tqdm(assignment_qs, desc="EvaluatorAssignments"):
            ea.update_cached_values()

        # 3. Backfill TechnicalEvaluationRound
        self.stdout.write(self.style.WARNING("Updating TechnicalEvaluationRounds..."))
        round_qs = TechnicalEvaluationRound.objects.all()
        for tr in tqdm(round_qs, desc="TechnicalEvaluationRounds"):
            tr.update_cached_values()

        self.stdout.write(self.style.SUCCESS("All caches updated."))

