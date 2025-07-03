# tech_eval/management/commands/debug_cache_data.py

from django.core.management.base import BaseCommand
from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment, CriteriaEvaluation
from django.db import connection

class Command(BaseCommand):
    help = 'Debug cache data issues'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--proposal-id',
            type=str,
            help='Specific proposal ID to debug'
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix the cache data'
        )
    
    def handle(self, *args, **options):
        proposal_id = options.get('proposal_id')
        fix_mode = options.get('fix')
        
        if proposal_id:
            self.debug_specific_proposal(proposal_id, fix_mode)
        else:
            self.debug_all_proposals(fix_mode)
    
    def debug_specific_proposal(self, proposal_id, fix_mode):
        """Debug a specific proposal"""
        try:
            # Find the evaluation round
            try:
                eval_round = TechnicalEvaluationRound.objects.get(
                    proposal__proposal_id=proposal_id
                )
            except TechnicalEvaluationRound.DoesNotExist:
                self.stdout.write(f"No evaluation round found for proposal {proposal_id}")
                return
            
            self.stdout.write(f"\n=== DEBUGGING PROPOSAL {proposal_id} ===")
            self.stdout.write(f"Evaluation Round ID: {eval_round.id}")
            
            # Check cached fields
            self.stdout.write(f"\nCACHED FIELDS:")
            self.stdout.write(f"  cached_assigned_count: {eval_round.cached_assigned_count}")
            self.stdout.write(f"  cached_completed_count: {eval_round.cached_completed_count}")
            self.stdout.write(f"  cached_average_percentage: {eval_round.cached_average_percentage}")
            self.stdout.write(f"  cached_evaluator_data exists: {bool(eval_round.cached_evaluator_data)}")
            self.stdout.write(f"  cached_marks_summary exists: {bool(eval_round.cached_marks_summary)}")
            
            # Check actual assignments
            assignments = eval_round.evaluator_assignments.all()
            self.stdout.write(f"\nACTUAL ASSIGNMENTS:")
            self.stdout.write(f"  Total assignments: {assignments.count()}")
            self.stdout.write(f"  Completed assignments: {assignments.filter(is_completed=True).count()}")
            
            for assignment in assignments:
                self.stdout.write(f"\n  Assignment {assignment.id}:")
                self.stdout.write(f"    Evaluator: {assignment.evaluator}")
                self.stdout.write(f"    Is completed: {assignment.is_completed}")
                self.stdout.write(f"    Expected TRL: {assignment.expected_trl}")
                self.stdout.write(f"    Conflict of interest: {assignment.conflict_of_interest}")
                
                # Check cached assignment fields
                self.stdout.write(f"    Cached raw marks: {assignment.cached_raw_marks}")
                self.stdout.write(f"    Cached percentage score: {assignment.cached_percentage_score}")
                self.stdout.write(f"    Cached criteria count: {assignment.cached_criteria_count}")
                
                # Check criteria evaluations
                criteria_evals = assignment.criteria_evaluations.all()
                self.stdout.write(f"    Criteria evaluations: {criteria_evals.count()}")
                
                for ce in criteria_evals:
                    self.stdout.write(f"      {ce.evaluation_criteria.name}: {ce.marks_given}/{ce.evaluation_criteria.total_marks}")
                    self.stdout.write(f"        Cached percentage: {ce.cached_percentage}")
            
            # Check cached evaluator data structure
            if eval_round.cached_evaluator_data:
                self.stdout.write(f"\nCACHED EVALUATOR DATA:")
                for i, evaluator_data in enumerate(eval_round.cached_evaluator_data):
                    self.stdout.write(f"  Evaluator {i+1}:")
                    for key, value in evaluator_data.items():
                        self.stdout.write(f"    {key}: {value}")
            
            # Check cached marks summary
            if eval_round.cached_marks_summary:
                self.stdout.write(f"\nCACHED MARKS SUMMARY:")
                for key, value in eval_round.cached_marks_summary.items():
                    if key == 'individual_marks':
                        self.stdout.write(f"  {key}: {len(value)} entries")
                        for mark in value:
                            self.stdout.write(f"    {mark}")
                    else:
                        self.stdout.write(f"  {key}: {value}")
            
            if fix_mode:
                self.stdout.write(f"\nFIXING CACHE FOR PROPOSAL {proposal_id}...")
                self.fix_proposal_cache(eval_round)
                
        except Exception as e:
            self.stdout.write(f"Error debugging proposal {proposal_id}: {e}")
    
    def debug_all_proposals(self, fix_mode):
        """Debug all proposals with issues"""
        self.stdout.write("=== DEBUGGING ALL PROPOSALS ===")
        
        # Find proposals with missing cache data
        rounds_with_issues = TechnicalEvaluationRound.objects.filter(
            evaluator_assignments__isnull=False,
            cached_evaluator_data__isnull=True
        ).distinct()
        
        self.stdout.write(f"Found {rounds_with_issues.count()} rounds with missing cache data")
        
        for eval_round in rounds_with_issues:
            proposal_id = getattr(eval_round.proposal, 'proposal_id', f'ID-{eval_round.proposal.id}')
            self.stdout.write(f"\nIssue with proposal: {proposal_id}")
            
            if fix_mode:
                self.fix_proposal_cache(eval_round)
    
    def fix_proposal_cache(self, eval_round):
        """Fix cache for a specific evaluation round"""
        try:
            self.stdout.write("  Updating assignment caches...")
            
            # First update all assignment caches
            for assignment in eval_round.evaluator_assignments.all():
                self.update_assignment_cache(assignment)
            
            self.stdout.write("  Updating round cache...")
            
            # Then update round cache
            self.update_round_cache(eval_round)
            
            self.stdout.write("  ✓ Cache updated successfully")
            
        except Exception as e:
            self.stdout.write(f"  ✗ Error fixing cache: {e}")
    
    def update_assignment_cache(self, assignment):
        """Update cache for an assignment"""
        if assignment.is_completed:
            criteria_evaluations = assignment.criteria_evaluations.select_related('evaluation_criteria')
            
            if criteria_evaluations.exists():
                raw_total = sum(float(ce.marks_given) for ce in criteria_evaluations)
                max_total = sum(float(ce.evaluation_criteria.total_marks) for ce in criteria_evaluations)
                
                assignment.cached_raw_marks = raw_total
                assignment.cached_max_marks = max_total
                assignment.cached_percentage_score = round((raw_total / max_total) * 100, 2) if max_total > 0 else 0
                assignment.cached_criteria_count = criteria_evaluations.count()
                
                # Cache criteria data
                criteria_data = []
                for ce in criteria_evaluations:
                    # Update criteria cache too
                    if ce.evaluation_criteria and ce.evaluation_criteria.total_marks:
                        total_marks = float(ce.evaluation_criteria.total_marks)
                        if total_marks > 0:
                            ce.cached_percentage = round((float(ce.marks_given) / total_marks) * 100, 2)
                            ce.cached_weighted_score = ce.cached_percentage
                            ce.save(update_fields=['cached_percentage', 'cached_weighted_score'])
                    
                    criteria_data.append({
                        'criteria_name': ce.evaluation_criteria.name,
                        'marks_given': float(ce.marks_given),
                        'max_marks': float(ce.evaluation_criteria.total_marks),
                        'percentage': ce.cached_percentage or 0,
                        'remarks': ce.remarks,
                    })
                
                assignment.cached_criteria_data = criteria_data
                assignment.save(update_fields=[
                    'cached_raw_marks', 'cached_max_marks', 'cached_percentage_score',
                    'cached_criteria_count', 'cached_criteria_data'
                ])
    
    def update_round_cache(self, eval_round):
        """Update cache for an evaluation round"""
        # Count assignments
        eval_round.cached_assigned_count = eval_round.evaluator_assignments.count()
        eval_round.cached_completed_count = eval_round.evaluator_assignments.filter(is_completed=True).count()
        
        # Calculate average percentage and build marks summary
        completed_assignments = eval_round.evaluator_assignments.filter(is_completed=True).select_related('evaluator')
        
        if completed_assignments.exists():
            total_percentage = 0
            valid_scores = 0
            marks_data = []
            evaluator_data = []
            
            for assignment in completed_assignments:
                # Refresh assignment to get updated cached values
                assignment.refresh_from_db()
                
                if assignment.cached_percentage_score is not None:
                    total_percentage += assignment.cached_percentage_score
                    valid_scores += 1
                    
                    marks_data.append({
                        'evaluator_name': assignment.evaluator.get_full_name() if hasattr(assignment.evaluator, 'get_full_name') else str(assignment.evaluator),
                        'evaluator_email': assignment.evaluator.email,
                        'percentage': assignment.cached_percentage_score,
                        'raw_marks': assignment.cached_raw_marks,
                        'max_marks': assignment.cached_max_marks,
                        'expected_trl': assignment.expected_trl,
                        'conflict_of_interest': assignment.conflict_of_interest,
                    })
                
                evaluator_data.append({
                    'id': assignment.evaluator.id,
                    'name': assignment.evaluator.get_full_name() if hasattr(assignment.evaluator, 'get_full_name') else str(assignment.evaluator),
                    'email': assignment.evaluator.email,
                    'is_completed': assignment.is_completed,
                    'expected_trl': assignment.expected_trl,
                    'conflict_of_interest': assignment.conflict_of_interest,
                    'percentage_score': assignment.cached_percentage_score,
                })
            
            if valid_scores > 0:
                eval_round.cached_average_percentage = round(total_percentage / valid_scores, 2)
                eval_round.cached_marks_summary = {
                    'average_percentage': eval_round.cached_average_percentage,
                    'total_evaluators': valid_scores,
                    'individual_marks': marks_data
                }
            else:
                eval_round.cached_average_percentage = None
                eval_round.cached_marks_summary = None
            
            eval_round.cached_evaluator_data = evaluator_data
        else:
            eval_round.cached_average_percentage = None
            eval_round.cached_marks_summary = None
            eval_round.cached_evaluator_data = []
        
        # Cache proposal data
        if eval_round.proposal:
            proposal = eval_round.proposal
            proposal_data = {
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
            eval_round.cached_proposal_data = proposal_data
        
        # Save with specific fields
        eval_round.save(update_fields=[
            'cached_assigned_count', 'cached_completed_count', 'cached_average_percentage', 
            'cached_marks_summary', 'cached_evaluator_data', 'cached_proposal_data', 'cache_updated_at'
        ])