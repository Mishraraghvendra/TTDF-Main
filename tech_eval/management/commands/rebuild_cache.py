# tech_eval/management/commands/rebuild_cache.py

from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.db.models.signals import post_save, post_delete
from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment, CriteriaEvaluation
import time
import sys

class Command(BaseCommand):
    help = 'Rebuild cached values for tech_eval models safely and efficiently'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process in each batch (default: 100)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )
        parser.add_argument(
            '--model',
            type=str,
            choices=['criteria', 'assignments', 'rounds', 'all'],
            default='all',
            help='Which models to update (default: all)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress information'
        )
    
    def handle(self, *args, **options):
        self.batch_size = options['batch_size']
        self.dry_run = options['dry_run']
        self.model_type = options['model']
        self.verbose = options['verbose']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting cache rebuild for: {self.model_type} '
                f'(batch size: {self.batch_size})'
            )
        )
        
        start_time = time.time()
        
        # Disable all signals to prevent cascading updates
        self._disable_signals()
        
        try:
            with transaction.atomic():
                if self.model_type in ['criteria', 'all']:
                    self._update_criteria_evaluations()
                
                if self.model_type in ['assignments', 'all']:
                    self._update_evaluator_assignments()
                
                if self.model_type in ['rounds', 'all']:
                    self._update_evaluation_rounds()
            
            elapsed = time.time() - start_time
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nCache rebuild completed in {elapsed:.2f} seconds'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Cache rebuild failed: {e}')
            )
            raise
        finally:
            self._enable_signals()
    
    def _disable_signals(self):
        """Disable all tech_eval signals to prevent recursion"""
        try:
            # Store original signal state
            self._signals_disabled = True
            
            # Get all signal receivers for our models
            post_save_receivers = post_save._live_receivers(sender=EvaluatorAssignment)
            post_delete_receivers = post_delete._live_receivers(sender=EvaluatorAssignment)
            
            # Disconnect signals
            for receiver in post_save_receivers:
                post_save.disconnect(receiver, sender=EvaluatorAssignment)
            for receiver in post_delete_receivers:
                post_delete.disconnect(receiver, sender=EvaluatorAssignment)
            
            post_save_receivers = post_save._live_receivers(sender=CriteriaEvaluation)
            post_delete_receivers = post_delete._live_receivers(sender=CriteriaEvaluation)
            
            for receiver in post_save_receivers:
                post_save.disconnect(receiver, sender=CriteriaEvaluation)
            for receiver in post_delete_receivers:
                post_delete.disconnect(receiver, sender=CriteriaEvaluation)
            
            if self.verbose:
                self.stdout.write('✓ Signals disabled')
                
        except Exception as e:
            if self.verbose:
                self.stdout.write(f'Warning: Could not disable all signals: {e}')
    
    def _enable_signals(self):
        """Re-enable signals (Django will auto-reconnect on next import)"""
        if self.verbose:
            self.stdout.write('✓ Signals will be re-enabled on next model import')
    
    def _update_criteria_evaluations(self):
        """Update cached values for criteria evaluations using bulk operations"""
        self.stdout.write('Processing criteria evaluations...')
        
        # Use raw SQL for better performance
        with connection.cursor() as cursor:
            # Get count first
            cursor.execute("""
                SELECT COUNT(*) FROM tech_eval_criteriaevaluation ce
                JOIN app_eval_evaluationitem ei ON ce.evaluation_criteria_id = ei.id
                WHERE ei.total_marks > 0
            """)
            total_count = cursor.fetchone()[0]
            
            if total_count == 0:
                self.stdout.write('No criteria evaluations to update')
                return
            
            self.stdout.write(f'Found {total_count} criteria evaluations to update')
            
            if self.dry_run:
                self.stdout.write(f'Would update {total_count} criteria evaluations')
                return
            
            # Update in batches using raw SQL for performance
            updated_count = 0
            for offset in range(0, total_count, self.batch_size):
                cursor.execute("""
                    UPDATE tech_eval_criteriaevaluation 
                    SET cached_percentage = ROUND((marks_given * 100.0 / ei.total_marks), 2),
                        cached_weighted_score = ROUND((marks_given * 100.0 / ei.total_marks), 2)
                    FROM app_eval_evaluationitem ei 
                    WHERE tech_eval_criteriaevaluation.evaluation_criteria_id = ei.id 
                    AND ei.total_marks > 0
                    AND tech_eval_criteriaevaluation.id IN (
                        SELECT ce2.id FROM tech_eval_criteriaevaluation ce2
                        JOIN app_eval_evaluationitem ei2 ON ce2.evaluation_criteria_id = ei2.id
                        WHERE ei2.total_marks > 0
                        ORDER BY ce2.id
                        LIMIT %s OFFSET %s
                    )
                """, [self.batch_size, offset])
                
                batch_updated = cursor.rowcount
                updated_count += batch_updated
                
                if self.verbose:
                    progress = min(offset + self.batch_size, total_count)
                    sys.stdout.write(f'\rProcessed {progress}/{total_count} criteria evaluations')
                    sys.stdout.flush()
            
            if self.verbose:
                print()  # New line after progress
            self.stdout.write(self.style.SUCCESS(f'✓ Updated {updated_count} criteria evaluations'))
    
    def _update_evaluator_assignments(self):
        """Update cached values for evaluator assignments"""
        self.stdout.write('Processing evaluator assignments...')
        
        # Get completed assignments with criteria
        queryset = EvaluatorAssignment.objects.filter(
            is_completed=True,
            criteria_evaluations__isnull=False
        ).distinct().prefetch_related('criteria_evaluations__evaluation_criteria')
        
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write('No completed assignments to update')
            return
        
        self.stdout.write(f'Found {total_count} completed assignments to update')
        
        if self.dry_run:
            self.stdout.write(f'Would update {total_count} assignments')
            return
        
        updated_count = 0
        
        # Process in batches
        for i in range(0, total_count, self.batch_size):
            batch = queryset[i:i + self.batch_size]
            
            # Prepare bulk update data
            updates = []
            
            for assignment in batch:
                criteria_evaluations = assignment.criteria_evaluations.filter(
                    evaluation_criteria__total_marks__gt=0
                )
                
                if criteria_evaluations.exists():
                    raw_total = sum(float(ce.marks_given) for ce in criteria_evaluations)
                    max_total = sum(
                        float(ce.evaluation_criteria.total_marks) 
                        for ce in criteria_evaluations
                    )
                    
                    if max_total > 0:
                        percentage = round((raw_total / max_total) * 100, 2)
                        
                        updates.append({
                            'id': assignment.id,
                            'cached_raw_marks': raw_total,
                            'cached_max_marks': max_total,
                            'cached_percentage_score': percentage,
                            'cached_criteria_count': criteria_evaluations.count()
                        })
            
            # Bulk update using raw SQL for better performance
            if updates:
                with connection.cursor() as cursor:
                    for update_data in updates:
                        cursor.execute("""
                            UPDATE tech_eval_evaluatorassignment 
                            SET cached_raw_marks = %s,
                                cached_max_marks = %s,
                                cached_percentage_score = %s,
                                cached_criteria_count = %s
                            WHERE id = %s
                        """, [
                            update_data['cached_raw_marks'],
                            update_data['cached_max_marks'],
                            update_data['cached_percentage_score'],
                            update_data['cached_criteria_count'],
                            update_data['id']
                        ])
                
                updated_count += len(updates)
            
            if self.verbose:
                progress = min(i + self.batch_size, total_count)
                sys.stdout.write(f'\rProcessed {progress}/{total_count} assignments')
                sys.stdout.flush()
        
        if self.verbose:
            print()  # New line after progress
        self.stdout.write(self.style.SUCCESS(f'✓ Updated {updated_count} assignments'))
    
    def _update_evaluation_rounds(self):
        """Update cached values for evaluation rounds"""
        self.stdout.write('Processing evaluation rounds...')
        
        queryset = TechnicalEvaluationRound.objects.prefetch_related(
            'evaluator_assignments',
            'proposal',
            'proposal__service'
        )
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write('No evaluation rounds to update')
            return
        
        self.stdout.write(f'Found {total_count} evaluation rounds to update')
        
        if self.dry_run:
            self.stdout.write(f'Would update {total_count} evaluation rounds')
            return
        
        updated_count = 0
        
        # Process in batches
        for i in range(0, total_count, self.batch_size):
            batch = queryset[i:i + self.batch_size]
            
            # Prepare bulk update data
            updates = []
            
            for eval_round in batch:
                assigned_count = eval_round.evaluator_assignments.count()
                completed_count = eval_round.evaluator_assignments.filter(is_completed=True).count()
                
                # Calculate average percentage from completed assignments
                completed_assignments = eval_round.evaluator_assignments.filter(
                    is_completed=True,
                    cached_percentage_score__isnull=False
                )
                
                if completed_assignments.exists():
                    total_score = sum(
                        a.cached_percentage_score or 0 
                        for a in completed_assignments
                    )
                    avg_percentage = round(total_score / completed_assignments.count(), 2)
                else:
                    avg_percentage = None
                
                # Build proposal data cache
                proposal_data = {}
                if eval_round.proposal:
                    proposal = eval_round.proposal
                    proposal_data = {
                        'proposal_id': getattr(proposal, 'proposal_id', 'N/A'),
                        'call': getattr(proposal.service, 'name', 'N/A') if proposal.service else 'N/A',
                        'org_type': getattr(proposal, 'org_type', 'N/A'),
                        'subject': getattr(proposal, 'subject', 'N/A'),
                        'description': getattr(proposal, 'description', 'N/A')[:500],  # Limit length
                        'org_name': getattr(proposal, 'org_address_line1', 'N/A'),
                        'contact_person': getattr(proposal, 'contact_name', 'N/A'),
                        'contact_email': getattr(proposal, 'contact_email', 'N/A'),
                        'contact_phone': getattr(proposal, 'org_mobile', 'N/A'),
                    }
                
                updates.append({
                    'id': eval_round.id,
                    'cached_assigned_count': assigned_count,
                    'cached_completed_count': completed_count,
                    'cached_average_percentage': avg_percentage,
                    'cached_proposal_data': proposal_data
                })
            
            # Bulk update using Django ORM (JSONField is easier this way)
            for update_data in updates:
                TechnicalEvaluationRound.objects.filter(id=update_data['id']).update(
                    cached_assigned_count=update_data['cached_assigned_count'],
                    cached_completed_count=update_data['cached_completed_count'],
                    cached_average_percentage=update_data['cached_average_percentage'],
                    cached_proposal_data=update_data['cached_proposal_data']
                )
            
            updated_count += len(updates)
            
            if self.verbose:
                progress = min(i + self.batch_size, total_count)
                sys.stdout.write(f'\rProcessed {progress}/{total_count} evaluation rounds')
                sys.stdout.flush()
        
        if self.verbose:
            print()  # New line after progress
        self.stdout.write(self.style.SUCCESS(f'✓ Updated {updated_count} evaluation rounds'))
    
    def _log_summary(self):
        """Log summary of cached data"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('CACHE REBUILD SUMMARY')
        self.stdout.write('='*50)
        
        # Count records with cached data
        criteria_cached = CriteriaEvaluation.objects.exclude(cached_percentage__isnull=True).count()
        criteria_total = CriteriaEvaluation.objects.count()
        
        assignments_cached = EvaluatorAssignment.objects.exclude(cached_percentage_score__isnull=True).count()
        assignments_total = EvaluatorAssignment.objects.count()
        
        rounds_cached = TechnicalEvaluationRound.objects.exclude(cached_assigned_count=0).count()
        rounds_total = TechnicalEvaluationRound.objects.count()
        
        self.stdout.write(f'Criteria Evaluations: {criteria_cached}/{criteria_total} cached')
        self.stdout.write(f'Evaluator Assignments: {assignments_cached}/{assignments_total} cached')
        self.stdout.write(f'Evaluation Rounds: {rounds_cached}/{rounds_total} cached')
        self.stdout.write('='*50)