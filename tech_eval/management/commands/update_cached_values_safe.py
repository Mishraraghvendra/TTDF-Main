
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment, CriteriaEvaluation
from django.db import models
import time
import sys

class Command(BaseCommand):
    help = 'Update cached values safely without signal recursion'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            choices=['criteria', 'assignments', 'rounds', 'all'],
            default='all',
            help='Which model to update cached values for'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of records to process in each batch'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )
    
    def handle(self, *args, **options):
        start_time = time.time()
        model_type = options['model']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting cache update for: {model_type}')
        )
        
        # Disconnect signals to prevent recursion
        self.disconnect_signals()
        
        try:
            if model_type in ['criteria', 'all']:
                self.update_criteria_evaluations(batch_size, dry_run)
            
            if model_type in ['assignments', 'all']:
                self.update_evaluator_assignments(batch_size, dry_run)
            
            if model_type in ['rounds', 'all']:
                self.update_evaluation_rounds(batch_size, dry_run)
            
            elapsed = time.time() - start_time
            self.stdout.write(
                self.style.SUCCESS(
                    f'Cache update completed in {elapsed:.2f} seconds'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Cache update failed: {e}')
            )
            raise CommandError(f'Cache update failed: {e}')
        finally:
            self.reconnect_signals()
            self.stdout.write('Signals reconnected')
    
    def disconnect_signals(self):
        """Temporarily disconnect signals to prevent recursion"""
        try:
            from tech_eval.models import (
                update_evaluation_round_cache_on_assignment_change,
                update_assignment_cache_on_criteria_change,
                update_criteria_cache_on_save
            )
            
            post_save.disconnect(update_evaluation_round_cache_on_assignment_change, sender=EvaluatorAssignment)
            post_delete.disconnect(update_evaluation_round_cache_on_assignment_change, sender=EvaluatorAssignment)
            post_save.disconnect(update_assignment_cache_on_criteria_change, sender=CriteriaEvaluation)
            post_delete.disconnect(update_assignment_cache_on_criteria_change, sender=CriteriaEvaluation)
            post_save.disconnect(update_criteria_cache_on_save, sender=CriteriaEvaluation)
            
            self.stdout.write('✓ Signals disconnected')
        except Exception as e:
            self.stdout.write(f'Warning: Could not disconnect signals: {e}')
    
    def reconnect_signals(self):
        """Reconnect signals after processing"""
        try:
            from tech_eval.models import (
                update_evaluation_round_cache_on_assignment_change,
                update_assignment_cache_on_criteria_change,
                update_criteria_cache_on_save
            )
            
            post_save.connect(update_evaluation_round_cache_on_assignment_change, sender=EvaluatorAssignment)
            post_delete.connect(update_evaluation_round_cache_on_assignment_change, sender=EvaluatorAssignment)
            post_save.connect(update_assignment_cache_on_criteria_change, sender=CriteriaEvaluation)
            post_delete.connect(update_assignment_cache_on_criteria_change, sender=CriteriaEvaluation)
            post_save.connect(update_criteria_cache_on_save, sender=CriteriaEvaluation)
            
            self.stdout.write('✓ Signals reconnected')
        except Exception as e:
            self.stdout.write(f'Warning: Could not reconnect signals: {e}')
    
    def update_criteria_evaluations(self, batch_size, dry_run):
        """Update cached values for criteria evaluations"""
        self.stdout.write('Processing criteria evaluations...')
        
        queryset = CriteriaEvaluation.objects.select_related('evaluation_criteria')
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write('No criteria evaluations found')
            return
        
        self.stdout.write(f'Found {total_count} criteria evaluations')
        
        if dry_run:
            self.stdout.write(f'Would update {total_count} criteria evaluations')
            return
        
        updated_count = 0
        
        for i in range(0, total_count, batch_size):
            batch = queryset[i:i + batch_size]
            
            with transaction.atomic():
                for criteria_eval in batch:
                    try:
                        if criteria_eval.evaluation_criteria and criteria_eval.evaluation_criteria.total_marks:
                            total_marks = float(criteria_eval.evaluation_criteria.total_marks)
                            if total_marks > 0:
                                percentage = round((float(criteria_eval.marks_given) / total_marks) * 100, 2)
                                
                                CriteriaEvaluation.objects.filter(id=criteria_eval.id).update(
                                    cached_percentage=percentage,
                                    cached_weighted_score=percentage
                                )
                                updated_count += 1
                    except Exception as e:
                        self.stdout.write(f'Error updating criteria evaluation {criteria_eval.id}: {e}')
            
            progress = min(i + batch_size, total_count)
            sys.stdout.write(f'\rProcessed {progress}/{total_count} criteria evaluations')
            sys.stdout.flush()
        
        print()
        self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} criteria evaluations'))
    
    def update_evaluator_assignments(self, batch_size, dry_run):
        """Update cached values for evaluator assignments"""
        self.stdout.write('Processing evaluator assignments...')
        
        queryset = EvaluatorAssignment.objects.filter(is_completed=True).prefetch_related('criteria_evaluations')
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write('No completed assignments found')
            return
        
        self.stdout.write(f'Found {total_count} completed assignments')
        
        if dry_run:
            self.stdout.write(f'Would update {total_count} assignments')
            return
        
        updated_count = 0
        
        for i in range(0, total_count, batch_size):
            batch = queryset[i:i + batch_size]
            
            with transaction.atomic():
                for assignment in batch:
                    try:
                        criteria_evaluations = assignment.criteria_evaluations.all()
                        
                        if criteria_evaluations.exists():
                            raw_total = sum(float(ce.marks_given) for ce in criteria_evaluations)
                            max_total = sum(float(ce.evaluation_criteria.total_marks) 
                                          for ce in criteria_evaluations 
                                          if ce.evaluation_criteria and ce.evaluation_criteria.total_marks)
                            
                            percentage = round((raw_total / max_total) * 100, 2) if max_total > 0 else 0
                            
                            EvaluatorAssignment.objects.filter(id=assignment.id).update(
                                cached_raw_marks=raw_total,
                                cached_max_marks=max_total,
                                cached_percentage_score=percentage,
                                cached_criteria_count=criteria_evaluations.count()
                            )
                            updated_count += 1
                    except Exception as e:
                        self.stdout.write(f'Error updating assignment {assignment.id}: {e}')
            
            progress = min(i + batch_size, total_count)
            sys.stdout.write(f'\rProcessed {progress}/{total_count} assignments')
            sys.stdout.flush()
        
        print()
        self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} assignments'))
    
    def update_evaluation_rounds(self, batch_size, dry_run):
        """Update cached values for evaluation rounds"""
        self.stdout.write('Processing evaluation rounds...')
        
        queryset = TechnicalEvaluationRound.objects.prefetch_related('evaluator_assignments', 'proposal', 'proposal__service')
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write('No evaluation rounds found')
            return
        
        self.stdout.write(f'Found {total_count} evaluation rounds')
        
        if dry_run:
            self.stdout.write(f'Would update {total_count} evaluation rounds')
            return
        
        updated_count = 0
        
        for i in range(0, total_count, batch_size):
            batch = queryset[i:i + batch_size]
            
            with transaction.atomic():
                for eval_round in batch:
                    try:
                        assigned_count = eval_round.evaluator_assignments.count()
                        completed_count = eval_round.evaluator_assignments.filter(is_completed=True).count()
                        
                        # Calculate average from assignment scores
                        completed_assignments = eval_round.evaluator_assignments.filter(
                            is_completed=True,
                            cached_percentage_score__isnull=False
                        )
                        
                        if completed_assignments.exists():
                            avg_percentage = completed_assignments.aggregate(
                                avg=models.Avg('cached_percentage_score')
                            )['avg']
                            avg_percentage = round(avg_percentage, 2) if avg_percentage else None
                        else:
                            avg_percentage = None
                        
                        # Cache proposal data
                        proposal_data = {}
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
                            }
                        
                        TechnicalEvaluationRound.objects.filter(id=eval_round.id).update(
                            cached_assigned_count=assigned_count,
                            cached_completed_count=completed_count,
                            cached_average_percentage=avg_percentage,
                            cached_proposal_data=proposal_data
                        )
                        updated_count += 1
                        
                    except Exception as e:
                        self.stdout.write(f'Error updating evaluation round {eval_round.id}: {e}')
            
            progress = min(i + batch_size, total_count)
            sys.stdout.write(f'\rProcessed {progress}/{total_count} evaluation rounds')
            sys.stdout.flush()
        
        print()
        self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} evaluation rounds'))
