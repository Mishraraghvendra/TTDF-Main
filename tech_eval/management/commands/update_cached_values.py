# tech_eval/management/commands/update_cached_values.py

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment, CriteriaEvaluation
import time
import sys

class Command(BaseCommand):
    help = 'Update cached values for existing technical evaluation records'
    
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
            default=100,
            help='Number of records to process in each batch'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if cached values exist'
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
        force_update = options['force']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting cache update for: {model_type}')
        )
        
        try:
            if model_type in ['criteria', 'all']:
                self.update_criteria_evaluations(batch_size, force_update, dry_run)
            
            if model_type in ['assignments', 'all']:
                self.update_evaluator_assignments(batch_size, force_update, dry_run)
            
            if model_type in ['rounds', 'all']:
                self.update_evaluation_rounds(batch_size, force_update, dry_run)
            
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
    
    def update_criteria_evaluations(self, batch_size, force_update, dry_run):
        """Update cached values for criteria evaluations"""
        self.stdout.write('Processing criteria evaluations...')
        
        try:
            queryset = CriteriaEvaluation.objects.select_related('evaluation_criteria')
            if not force_update:
                queryset = queryset.filter(cached_percentage__isnull=True)
        except Exception as e:
            self.stdout.write(f'Error accessing CriteriaEvaluation: {e}')
            self.stdout.write('Skipping criteria evaluations - table may not exist yet')
            return
        
        total_count = queryset.count()
        if total_count == 0:
            self.stdout.write('No criteria evaluations to update')
            return
        
        updated_count = 0
        error_count = 0
        
        self.stdout.write(f'Found {total_count} criteria evaluations to update')
        
        if dry_run:
            self.stdout.write(f'Would update {total_count} criteria evaluations')
            return
        
        for i in range(0, total_count, batch_size):
            batch = queryset[i:i + batch_size]
            
            try:
                with transaction.atomic():
                    for criteria_eval in batch:
                        try:
                            if hasattr(criteria_eval, 'evaluation_criteria') and criteria_eval.evaluation_criteria:
                                if hasattr(criteria_eval.evaluation_criteria, 'total_marks') and criteria_eval.evaluation_criteria.total_marks:
                                    total_marks = float(criteria_eval.evaluation_criteria.total_marks)
                                    if total_marks > 0:
                                        percentage = round((float(criteria_eval.marks_given) / total_marks) * 100, 2)
                                        
                                        # Only update if field exists
                                        if hasattr(criteria_eval, 'cached_percentage'):
                                            criteria_eval.cached_percentage = percentage
                                        
                                        # Calculate weighted score if weightage exists
                                        weightage = getattr(criteria_eval.evaluation_criteria, 'weightage', 0)
                                        if weightage and hasattr(criteria_eval, 'cached_weighted_score'):
                                            criteria_eval.cached_weighted_score = round((percentage / 100) * float(weightage), 2)
                                        elif hasattr(criteria_eval, 'cached_weighted_score'):
                                            criteria_eval.cached_weighted_score = percentage
                                        
                                        # Save only if fields exist
                                        update_fields = []
                                        if hasattr(criteria_eval, 'cached_percentage'):
                                            update_fields.append('cached_percentage')
                                        if hasattr(criteria_eval, 'cached_weighted_score'):
                                            update_fields.append('cached_weighted_score')
                                        
                                        if update_fields:
                                            criteria_eval.save(update_fields=update_fields)
                                            updated_count += 1
                        except Exception as e:
                            error_count += 1
                            self.stdout.write(f'Error updating criteria evaluation {criteria_eval.id}: {e}')
            except Exception as e:
                self.stdout.write(f'Error processing batch {i}-{i+batch_size}: {e}')
            
            # Progress indicator
            if (i + batch_size) % (batch_size * 10) == 0 or (i + batch_size) >= total_count:
                progress = min(i + batch_size, total_count)
                sys.stdout.write(f'\rUpdated {progress}/{total_count} criteria evaluations')
                sys.stdout.flush()
        
        print()  # New line after progress indicator
        self.stdout.write(
            self.style.SUCCESS(f'Updated {updated_count} criteria evaluations')
        )
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'{error_count} errors occurred')
            )
    
    def update_evaluator_assignments(self, batch_size, force_update, dry_run):
        """Update cached values for evaluator assignments"""
        self.stdout.write('Processing evaluator assignments...')
        
        try:
            queryset = EvaluatorAssignment.objects.prefetch_related('criteria_evaluations__evaluation_criteria')
            if not force_update:
                queryset = queryset.filter(is_completed=True, cached_percentage_score__isnull=True)
        except Exception as e:
            self.stdout.write(f'Error accessing EvaluatorAssignment: {e}')
            self.stdout.write('Skipping assignments - some fields may not exist yet')
            return
        
        total_count = queryset.count()
        if total_count == 0:
            self.stdout.write('No assignments to update')
            return
        
        updated_count = 0
        error_count = 0
        
        self.stdout.write(f'Found {total_count} assignments to update')
        
        if dry_run:
            self.stdout.write(f'Would update {total_count} assignments')
            return
        
        for i in range(0, total_count, batch_size):
            batch = queryset[i:i + batch_size]
            
            try:
                with transaction.atomic():
                    for assignment in batch:
                        try:
                            if assignment.is_completed:
                                criteria_evaluations = assignment.criteria_evaluations.all()
                                
                                if criteria_evaluations.exists():
                                    raw_total = sum(float(ce.marks_given) for ce in criteria_evaluations)
                                    max_total = sum(float(ce.evaluation_criteria.total_marks) for ce in criteria_evaluations if ce.evaluation_criteria.total_marks)
                                    
                                    # Only update fields that exist
                                    update_fields = []
                                    
                                    if hasattr(assignment, 'cached_raw_marks'):
                                        assignment.cached_raw_marks = raw_total
                                        update_fields.append('cached_raw_marks')
                                    
                                    if hasattr(assignment, 'cached_max_marks'):
                                        assignment.cached_max_marks = max_total
                                        update_fields.append('cached_max_marks')
                                    
                                    if hasattr(assignment, 'cached_percentage_score'):
                                        assignment.cached_percentage_score = round((raw_total / max_total) * 100, 2) if max_total > 0 else 0
                                        update_fields.append('cached_percentage_score')
                                    
                                    if hasattr(assignment, 'cached_criteria_count'):
                                        assignment.cached_criteria_count = criteria_evaluations.count()
                                        update_fields.append('cached_criteria_count')
                                    
                                    # Cache criteria data if field exists
                                    if hasattr(assignment, 'cached_criteria_data'):
                                        criteria_data = []
                                        for ce in criteria_evaluations:
                                            criteria_data.append({
                                                'criteria_name': ce.evaluation_criteria.name if ce.evaluation_criteria else 'Unknown',
                                                'marks_given': float(ce.marks_given),
                                                'max_marks': float(ce.evaluation_criteria.total_marks) if ce.evaluation_criteria and ce.evaluation_criteria.total_marks else 0,
                                                'percentage': round((float(ce.marks_given) / float(ce.evaluation_criteria.total_marks)) * 100, 2) if ce.evaluation_criteria and ce.evaluation_criteria.total_marks and float(ce.evaluation_criteria.total_marks) > 0 else 0,
                                                'remarks': ce.remarks if hasattr(ce, 'remarks') else '',
                                            })
                                        assignment.cached_criteria_data = criteria_data
                                        update_fields.append('cached_criteria_data')
                                else:
                                    # Clear cache if not completed
                                    update_fields = []
                                    if hasattr(assignment, 'cached_raw_marks'):
                                        assignment.cached_raw_marks = 0
                                        update_fields.append('cached_raw_marks')
                                    if hasattr(assignment, 'cached_max_marks'):
                                        assignment.cached_max_marks = 0
                                        update_fields.append('cached_max_marks')
                                    if hasattr(assignment, 'cached_percentage_score'):
                                        assignment.cached_percentage_score = 0
                                        update_fields.append('cached_percentage_score')
                                    if hasattr(assignment, 'cached_criteria_count'):
                                        assignment.cached_criteria_count = 0
                                        update_fields.append('cached_criteria_count')
                                    if hasattr(assignment, 'cached_criteria_data'):
                                        assignment.cached_criteria_data = []
                                        update_fields.append('cached_criteria_data')
                            else:
                                # Clear cache if not completed
                                update_fields = []
                                for field in ['cached_raw_marks', 'cached_max_marks', 'cached_percentage_score']:
                                    if hasattr(assignment, field):
                                        setattr(assignment, field, None)
                                        update_fields.append(field)
                                for field in ['cached_criteria_count']:
                                    if hasattr(assignment, field):
                                        setattr(assignment, field, 0)
                                        update_fields.append(field)
                                if hasattr(assignment, 'cached_criteria_data'):
                                    assignment.cached_criteria_data = None
                                    update_fields.append('cached_criteria_data')
                            
                            if update_fields:
                                assignment.save(update_fields=update_fields)
                                updated_count += 1
                            
                        except Exception as e:
                            error_count += 1
                            self.stdout.write(f'Error updating assignment {assignment.id}: {e}')
            except Exception as e:
                self.stdout.write(f'Error processing assignment batch {i}-{i+batch_size}: {e}')
            
            # Progress indicator
            if (i + batch_size) % (batch_size * 10) == 0 or (i + batch_size) >= total_count:
                progress = min(i + batch_size, total_count)
                sys.stdout.write(f'\rUpdated {progress}/{total_count} assignments')
                sys.stdout.flush()
        
        print()  # New line after progress indicator
        self.stdout.write(
            self.style.SUCCESS(f'Updated {updated_count} assignments')
        )
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'{error_count} errors occurred')
            )
    
    def update_evaluation_rounds(self, batch_size, force_update, dry_run):
        """Update cached values for evaluation rounds"""
        self.stdout.write('Processing evaluation rounds...')
        
        try:
            queryset = TechnicalEvaluationRound.objects.prefetch_related(
                'evaluator_assignments__evaluator',
                'evaluator_assignments__criteria_evaluations__evaluation_criteria',
                'proposal',
                'proposal__applicant'
            )
            if not force_update:
                queryset = queryset.filter(cached_assigned_count=0)
        except Exception as e:
            self.stdout.write(f'Error accessing TechnicalEvaluationRound: {e}')
            self.stdout.write('Skipping evaluation rounds - some fields may not exist yet')
            return
        
        total_count = queryset.count()
        if total_count == 0:
            self.stdout.write('No evaluation rounds to update')
            return
        
        updated_count = 0
        error_count = 0
        
        self.stdout.write(f'Found {total_count} evaluation rounds to update')
        
        if dry_run:
            self.stdout.write(f'Would update {total_count} evaluation rounds')
            return
        
        for i in range(0, total_count, batch_size):
            batch = queryset[i:i + batch_size]
            
            try:
                with transaction.atomic():
                    for eval_round in batch:
                        try:
                            update_fields = []
                            
                            # Count assignments
                            if hasattr(eval_round, 'cached_assigned_count'):
                                eval_round.cached_assigned_count = eval_round.evaluator_assignments.count()
                                update_fields.append('cached_assigned_count')
                            
                            if hasattr(eval_round, 'cached_completed_count'):
                                eval_round.cached_completed_count = eval_round.evaluator_assignments.filter(is_completed=True).count()
                                update_fields.append('cached_completed_count')
                            
                            # Calculate average percentage and build marks summary
                            completed_assignments = eval_round.evaluator_assignments.filter(is_completed=True)
                            
                            if completed_assignments.exists():
                                total_percentage = 0
                                valid_scores = 0
                                marks_data = []
                                evaluator_data = []
                                
                                for assignment in completed_assignments:
                                    # Calculate percentage for this assignment
                                    try:
                                        criteria_evaluations = assignment.criteria_evaluations.all()
                                        if criteria_evaluations.exists():
                                            raw_total = sum(float(ce.marks_given) for ce in criteria_evaluations)
                                            max_total = sum(float(ce.evaluation_criteria.total_marks) for ce in criteria_evaluations if ce.evaluation_criteria and ce.evaluation_criteria.total_marks)
                                            percentage = round((raw_total / max_total) * 100, 2) if max_total > 0 else 0
                                            
                                            total_percentage += percentage
                                            valid_scores += 1
                                            
                                            marks_data.append({
                                                'evaluator_name': assignment.evaluator.get_full_name() if hasattr(assignment.evaluator, 'get_full_name') else str(assignment.evaluator),
                                                'evaluator_email': getattr(assignment.evaluator, 'email', 'N/A'),
                                                'percentage': percentage,
                                                'raw_marks': raw_total,
                                                'max_marks': max_total,
                                                'expected_trl': getattr(assignment, 'expected_trl', None),
                                                'conflict_of_interest': getattr(assignment, 'conflict_of_interest', False),
                                            })
                                    except Exception as e:
                                        self.stdout.write(f'Error calculating assignment {assignment.id}: {e}')
                                    
                                    evaluator_data.append({
                                        'id': assignment.evaluator.id,
                                        'name': assignment.evaluator.get_full_name() if hasattr(assignment.evaluator, 'get_full_name') else str(assignment.evaluator),
                                        'email': getattr(assignment.evaluator, 'email', 'N/A'),
                                        'is_completed': assignment.is_completed,
                                        'expected_trl': getattr(assignment, 'expected_trl', None),
                                        'conflict_of_interest': getattr(assignment, 'conflict_of_interest', False),
                                        'percentage_score': percentage if 'percentage' in locals() else None,
                                    })
                                
                                if valid_scores > 0 and hasattr(eval_round, 'cached_average_percentage'):
                                    eval_round.cached_average_percentage = round(total_percentage / valid_scores, 2)
                                    update_fields.append('cached_average_percentage')
                                
                                if hasattr(eval_round, 'cached_marks_summary'):
                                    eval_round.cached_marks_summary = {
                                        'average_percentage': eval_round.cached_average_percentage if hasattr(eval_round, 'cached_average_percentage') else None,
                                        'total_evaluators': valid_scores,
                                        'individual_marks': marks_data
                                    }
                                    update_fields.append('cached_marks_summary')
                                
                                if hasattr(eval_round, 'cached_evaluator_data'):
                                    eval_round.cached_evaluator_data = evaluator_data
                                    update_fields.append('cached_evaluator_data')
                            else:
                                if hasattr(eval_round, 'cached_average_percentage'):
                                    eval_round.cached_average_percentage = None
                                    update_fields.append('cached_average_percentage')
                                if hasattr(eval_round, 'cached_marks_summary'):
                                    eval_round.cached_marks_summary = None
                                    update_fields.append('cached_marks_summary')
                                if hasattr(eval_round, 'cached_evaluator_data'):
                                    eval_round.cached_evaluator_data = []
                                    update_fields.append('cached_evaluator_data')
                            
                            # Cache proposal data for faster access
                            if eval_round.proposal and hasattr(eval_round, 'cached_proposal_data'):
                                import json
                                proposal_data = {
                                    'proposal_id': getattr(eval_round.proposal, 'proposal_id', None),
                                    'created_at': eval_round.proposal.created_at.isoformat() if hasattr(eval_round.proposal, 'created_at') and eval_round.proposal.created_at else None,
                                }
                                
                                # Parse form_data if available
                                if hasattr(eval_round.proposal, 'form_data') and eval_round.proposal.form_data:
                                    try:
                                        form_data = json.loads(eval_round.proposal.form_data) if isinstance(eval_round.proposal.form_data, str) else eval_round.proposal.form_data
                                        proposal_data.update({
                                            'call': form_data.get('call_name', 'N/A'),
                                            'org_type': form_data.get('organization_type', 'N/A'),
                                            'subject': form_data.get('project_title', 'N/A'),
                                            'description': form_data.get('project_description', 'N/A'),
                                        })
                                    except (json.JSONDecodeError, TypeError):
                                        proposal_data.update({
                                            'call': 'N/A',
                                            'org_type': 'N/A',
                                            'subject': 'N/A',
                                            'description': 'N/A',
                                        })
                                
                                # Add applicant data
                                if hasattr(eval_round.proposal, 'applicant') and eval_round.proposal.applicant:
                                    applicant = eval_round.proposal.applicant
                                    proposal_data.update({
                                        'org_name': getattr(applicant, 'organization_name', 'N/A'),
                                        'contact_person': f"{getattr(applicant, 'first_name', '')} {getattr(applicant, 'last_name', '')}".strip() or 'N/A',
                                        'contact_email': getattr(applicant, 'email', 'N/A'),
                                        'contact_phone': getattr(applicant, 'phone', 'N/A'),
                                    })
                                
                                eval_round.cached_proposal_data = proposal_data
                                update_fields.append('cached_proposal_data')
                            
                            # Add cache_updated_at if it exists
                            if hasattr(eval_round, 'cache_updated_at'):
                                update_fields.append('cache_updated_at')
                            
                            # Save with specific fields to avoid recursion
                            if update_fields:
                                eval_round.save(update_fields=update_fields)
                                updated_count += 1
                            
                        except Exception as e:
                            error_count += 1
                            self.stdout.write(f'Error updating evaluation round {eval_round.id}: {e}')
            except Exception as e:
                self.stdout.write(f'Error processing round batch {i}-{i+batch_size}: {e}')
            
            # Progress indicator
            if (i + batch_size) % (batch_size * 5) == 0 or (i + batch_size) >= total_count:
                progress = min(i + batch_size, total_count)
                sys.stdout.write(f'\rUpdated {progress}/{total_count} evaluation rounds')
                sys.stdout.flush()
        
        print()  # New line after progress indicator
        self.stdout.write(
            self.style.SUCCESS(f'Updated {updated_count} evaluation rounds')
        )
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'{error_count} errors occurred')
            )