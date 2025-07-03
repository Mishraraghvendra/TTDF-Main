# tech_eval/management/commands/fix_evaluator_cache.py

from django.core.management.base import BaseCommand
from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment
from django.db import transaction
import time

class Command(BaseCommand):
    help = 'Fix missing evaluator data in cache'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Batch size for processing'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        verbose = options['verbose']
        
        start_time = time.time()
        
        self.stdout.write("=== FIXING EVALUATOR CACHE DATA ===")
        
        # Find rounds with missing evaluator data but have assignments
        problematic_rounds = TechnicalEvaluationRound.objects.filter(
            evaluator_assignments__isnull=False,
            cached_evaluator_data__isnull=True
        ).distinct()
        
        total_count = problematic_rounds.count()
        self.stdout.write(f"Found {total_count} rounds with missing evaluator cache data")
        
        if total_count == 0:
            self.stdout.write("No issues found!")
            return
        
        fixed_count = 0
        
        # Process in batches
        for i in range(0, total_count, batch_size):
            batch = problematic_rounds[i:i + batch_size]
            
            with transaction.atomic():
                for eval_round in batch:
                    try:
                        self.fix_round_evaluator_cache(eval_round, verbose)
                        fixed_count += 1
                        
                        if verbose:
                            proposal_id = getattr(eval_round.proposal, 'proposal_id', f'ID-{eval_round.id}')
                            self.stdout.write(f"  ✓ Fixed {proposal_id}")
                        
                    except Exception as e:
                        proposal_id = getattr(eval_round.proposal, 'proposal_id', f'ID-{eval_round.id}')
                        self.stdout.write(f"  ✗ Error fixing {proposal_id}: {e}")
            
            # Show progress
            progress = min(i + batch_size, total_count)
            self.stdout.write(f"Progress: {progress}/{total_count} rounds processed")
        
        elapsed = time.time() - start_time
        self.stdout.write(f"\n✓ Fixed {fixed_count}/{total_count} rounds in {elapsed:.2f} seconds")
        
        # Verify the fix
        self.verify_fix()
    
    def fix_round_evaluator_cache(self, eval_round, verbose=False):
        """Fix the evaluator cache for a specific round"""
        
        # Get all assignments for this round
        assignments = eval_round.evaluator_assignments.select_related('evaluator').all()
        
        if not assignments.exists():
            if verbose:
                self.stdout.write(f"    No assignments found for round {eval_round.id}")
            return
        
        # Build evaluator data
        evaluator_data = []
        marks_data = []
        total_percentage = 0
        valid_scores = 0
        
        for assignment in assignments:
            # Build evaluator data entry
            evaluator_entry = {
                'id': assignment.evaluator.id,
                'name': assignment.evaluator.get_full_name() if hasattr(assignment.evaluator, 'get_full_name') else str(assignment.evaluator),
                'email': assignment.evaluator.email,
                'is_completed': assignment.is_completed,
                'expected_trl': assignment.expected_trl,
                'conflict_of_interest': assignment.conflict_of_interest,
                'percentage_score': assignment.cached_percentage_score,
            }
            evaluator_data.append(evaluator_entry)
            
            # If completed and has score, add to marks data
            if assignment.is_completed and assignment.cached_percentage_score is not None:
                marks_entry = {
                    'evaluator_name': evaluator_entry['name'],
                    'evaluator_email': evaluator_entry['email'],
                    'percentage': assignment.cached_percentage_score,
                    'raw_marks': assignment.cached_raw_marks,
                    'max_marks': assignment.cached_max_marks,
                    'expected_trl': assignment.expected_trl,
                    'conflict_of_interest': assignment.conflict_of_interest,
                }
                marks_data.append(marks_entry)
                total_percentage += assignment.cached_percentage_score
                valid_scores += 1
        
        # Calculate averages
        if valid_scores > 0:
            average_percentage = round(total_percentage / valid_scores, 2)
            marks_summary = {
                'average_percentage': average_percentage,
                'total_evaluators': valid_scores,
                'individual_marks': marks_data
            }
        else:
            average_percentage = None
            marks_summary = None
        
        # Update the evaluation round
        eval_round.cached_assigned_count = assignments.count()
        eval_round.cached_completed_count = assignments.filter(is_completed=True).count()
        eval_round.cached_evaluator_data = evaluator_data
        eval_round.cached_marks_summary = marks_summary
        eval_round.cached_average_percentage = average_percentage
        
        # Cache proposal data if missing
        if not eval_round.cached_proposal_data and eval_round.proposal:
            proposal = eval_round.proposal
            eval_round.cached_proposal_data = {
                'proposal_id': getattr(proposal, 'proposal_id', 'N/A'),
                'call': getattr(proposal.service, 'name', 'N/A') if proposal.service else 'N/A',
                'org_type': getattr(proposal, 'org_type', 'N/A'),
                'subject': getattr(proposal, 'subject', 'N/A'),
                'description': getattr(proposal, 'description', 'N/A'),
                'org_name': getattr(proposal, 'org_address_line1', 'N/A'),
                'contact_person': getattr(proposal, 'contact_name', 'N/A'),
                'contact_email': getattr(proposal, 'contact_email', 'N/A'),
                'contact_phone': getattr(proposal, 'org_mobile', 'N/A'),
                'created_at': proposal.created_at.isoformat() if hasattr(proposal, 'created_at') else None,
            }
        
        # Save with specific fields to avoid triggering signals
        eval_round.save(update_fields=[
            'cached_assigned_count', 'cached_completed_count', 'cached_evaluator_data',
            'cached_marks_summary', 'cached_average_percentage', 'cached_proposal_data', 'cache_updated_at'
        ])
        
        if verbose:
            self.stdout.write(f"    Updated: {len(evaluator_data)} evaluators, {valid_scores} completed")
    
    def verify_fix(self):
        """Verify that the fix worked"""
        self.stdout.write("\n=== VERIFICATION ===")
        
        # Count rounds still missing evaluator data
        still_missing = TechnicalEvaluationRound.objects.filter(
            evaluator_assignments__isnull=False,
            cached_evaluator_data__isnull=True
        ).distinct().count()
        
        # Count rounds with evaluator data
        with_evaluator_data = TechnicalEvaluationRound.objects.exclude(
            cached_evaluator_data__isnull=True
        ).count()
        
        # Count rounds with marks summary
        with_marks_summary = TechnicalEvaluationRound.objects.exclude(
            cached_marks_summary__isnull=True
        ).count()
        
        total_rounds = TechnicalEvaluationRound.objects.count()
        
        self.stdout.write(f"Total rounds: {total_rounds}")
        self.stdout.write(f"Rounds with evaluator data: {with_evaluator_data}")
        self.stdout.write(f"Rounds with marks summary: {with_marks_summary}")
        self.stdout.write(f"Still missing evaluator data: {still_missing}")
        
        if still_missing == 0:
            self.stdout.write(self.style.SUCCESS("✓ All evaluator cache data fixed!"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠ {still_missing} rounds still need fixing"))
        
        # Show sample of fixed data
        sample_round = TechnicalEvaluationRound.objects.exclude(
            cached_evaluator_data__isnull=True
        ).first()
        
        if sample_round and sample_round.cached_evaluator_data:
            self.stdout.write(f"\nSample evaluator data structure:")
            evaluator_sample = sample_round.cached_evaluator_data[0] if sample_round.cached_evaluator_data else {}
            for key, value in evaluator_sample.items():
                self.stdout.write(f"  {key}: {value}")
            
            if sample_round.cached_marks_summary:
                self.stdout.write(f"\nSample marks summary:")
                marks_summary = sample_round.cached_marks_summary
                self.stdout.write(f"  Average: {marks_summary.get('average_percentage')}")
                self.stdout.write(f"  Evaluators: {marks_summary.get('total_evaluators')}")
                self.stdout.write(f"  Individual marks: {len(marks_summary.get('individual_marks', []))}")