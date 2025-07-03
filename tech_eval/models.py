# tech_eval/models.py - COMPLETE FILE WITH CACHE FIX

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
import json
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class TechnicalEvaluationRound(models.Model):
    """
    Technical evaluation round with cached fields for performance
    """
    ASSIGNMENT_STATUS_CHOICES = [
        ('pending', 'Pending Assignment'),
        ('assigned', 'Assigned'),
        ('completed', 'Completed'),
    ]
    
    OVERALL_DECISION_CHOICES = [
        ('recommended', 'Recommended'),
        ('not_recommended', 'Not Recommended'),
        ('pending', 'Pending'),
    ]
    
    # Core fields
    proposal = models.ForeignKey(
        'dynamic_form.FormSubmission',
        on_delete=models.CASCADE,
        related_name='technical_evaluation_rounds',
        db_index=True
    )
    
    assignment_status = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    overall_decision = models.CharField(
        max_length=20,
        choices=OVERALL_DECISION_CHOICES,
        default='pending',
        db_index=True
    )
    
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='technical_evaluations_assigned'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # CACHED FIELDS for performance
    cached_assigned_count = models.IntegerField(default=0, db_index=True)
    cached_completed_count = models.IntegerField(default=0, db_index=True)
    cached_average_percentage = models.FloatField(null=True, blank=True, db_index=True)
    cached_marks_summary = models.JSONField(null=True, blank=True)
    cached_evaluator_data = models.JSONField(null=True, blank=True)
    cached_proposal_data = models.JSONField(null=True, blank=True)
    cache_updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['proposal']
        ordering = ['-created_at']
        verbose_name = "Technical Evaluation Round"
        verbose_name_plural = "Technical Evaluation Rounds"
        indexes = [
            models.Index(fields=['assignment_status', '-created_at']),
            models.Index(fields=['overall_decision', '-created_at']),
            models.Index(fields=['proposal', 'assignment_status']),
            models.Index(fields=['cached_assigned_count', 'cached_completed_count']),
            models.Index(fields=['cached_average_percentage']),
        ]
    
    def __str__(self):
        proposal_id = getattr(self.proposal, 'proposal_id', self.proposal.id) if self.proposal else 'Unknown'
        return f"Technical Evaluation - {proposal_id}"
    
    @property
    def assigned_evaluators_count(self):
        """Use cached count for performance"""
        return self.cached_assigned_count
    
    @property
    def completed_evaluations_count(self):
        """Use cached count for performance"""
        return self.cached_completed_count
    
    @property
    def average_percentage(self):
        """Use cached average percentage"""
        return self.cached_average_percentage
    
    @property
    def is_all_evaluations_completed(self):
        """Check if all evaluations completed using cached values"""
        return self.cached_assigned_count > 0 and self.cached_assigned_count == self.cached_completed_count
    
    @property
    def evaluation_progress_percentage(self):
        """Calculate progress using cached values"""
        if self.cached_assigned_count == 0:
            return 0
        return round((self.cached_completed_count / self.cached_assigned_count) * 100, 1)
    
    def update_cached_values(self):
        """Update all cached values - IMPROVED VERSION"""
        try:
            # Count assignments
            self.cached_assigned_count = self.evaluator_assignments.count()
            self.cached_completed_count = self.evaluator_assignments.filter(is_completed=True).count()
            
            # Calculate average percentage and build marks summary
            completed_assignments = self.evaluator_assignments.filter(is_completed=True).select_related('evaluator')
            
            if completed_assignments.exists():
                total_percentage = 0
                valid_scores = 0
                marks_data = []
                evaluator_data = []
                
                for assignment in completed_assignments:
                    # FORCE UPDATE assignment cache before using it
                    assignment.update_cached_values()
                    
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
                    self.cached_average_percentage = round(total_percentage / valid_scores, 2)
                    self.cached_marks_summary = {
                        'average_percentage': self.cached_average_percentage,
                        'total_evaluators': valid_scores,
                        'individual_marks': marks_data
                    }
                else:
                    self.cached_average_percentage = None
                    self.cached_marks_summary = None
                
                self.cached_evaluator_data = evaluator_data
            else:
                self.cached_average_percentage = None
                self.cached_marks_summary = None
                self.cached_evaluator_data = []
            
            # Cache proposal data
            if self.proposal:
                proposal = self.proposal
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
                self.cached_proposal_data = proposal_data
            
            # Save with specific fields to avoid recursion
            self.save(update_fields=[
                'cached_assigned_count', 
                'cached_completed_count', 
                'cached_average_percentage', 
                'cached_marks_summary',
                'cached_evaluator_data',
                'cached_proposal_data',
                'cache_updated_at'
            ])
            
            logger.info(f"Updated cached values for evaluation round {self.id}")
            
        except Exception as e:
            logger.error(f"Error updating cached values for evaluation round {self.id}: {e}")
    
    def get_fast_summary(self):
        """Get complete summary using only cached data"""
        return {
            'id': self.id,
            'assignment_status': self.assignment_status,
            'overall_decision': self.overall_decision,
            'assigned_evaluators_count': self.cached_assigned_count,
            'completed_evaluations_count': self.cached_completed_count,
            'average_percentage': self.cached_average_percentage,
            'evaluation_marks_summary': self.cached_marks_summary,
            'assigned_evaluators': self.cached_evaluator_data or [],
            'completed_evaluations': [e for e in (self.cached_evaluator_data or []) if e.get('is_completed')],
            'proposal_data': self.cached_proposal_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_all_completed': self.is_all_evaluations_completed,
            'progress_percentage': self.evaluation_progress_percentage,
        }


class EvaluatorAssignment(models.Model):
    """
    Evaluator assignment with cached calculations
    """
    evaluation_round = models.ForeignKey(
        TechnicalEvaluationRound,
        on_delete=models.CASCADE,
        related_name='evaluator_assignments',
        db_index=True
    )
    
    evaluator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='technical_evaluator_assignments',
        db_index=True
    )
    
    # TRL fields
    current_trl = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(9)],
        help_text="Current Technology Readiness Level (1-9)"
    )
    
    expected_trl = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(9)],
        help_text="Expected Technology Readiness Level after project completion (1-9)"
    )
    
    # Conflict of interest
    conflict_of_interest = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Does the evaluator have a conflict of interest?"
    )
    
    conflict_remarks = models.TextField(
        blank=True,
        help_text="Details about the conflict of interest"
    )
    
    # Evaluation status
    is_completed = models.BooleanField(default=False, db_index=True)
    overall_comments = models.TextField(blank=True)
    
    # CACHED FIELDS for performance
    cached_raw_marks = models.FloatField(null=True, blank=True)
    cached_max_marks = models.FloatField(null=True, blank=True)
    cached_percentage_score = models.FloatField(null=True, blank=True, db_index=True)
    cached_criteria_count = models.IntegerField(default=0)
    cached_criteria_data = models.JSONField(null=True, blank=True)
    
    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['evaluation_round', 'evaluator']
        ordering = ['-assigned_at']
        verbose_name = "Evaluator Assignment"
        verbose_name_plural = "Evaluator Assignments"
        indexes = [
            models.Index(fields=['evaluation_round', 'is_completed']),
            models.Index(fields=['evaluator', 'is_completed']),
            models.Index(fields=['is_completed', '-assigned_at']),
            models.Index(fields=['conflict_of_interest', 'is_completed']),
            models.Index(fields=['cached_percentage_score']),
        ]
    
    def __str__(self):
        evaluator_name = self.evaluator.get_full_name() if hasattr(self.evaluator, 'get_full_name') else str(self.evaluator)
        return f"{evaluator_name} - {self.evaluation_round}"
    
    @property
    def trl_improvement(self):
        """Calculate TRL improvement"""
        if self.current_trl and self.expected_trl:
            return self.expected_trl - self.current_trl
        return None
    
    @property
    def trl_improvement_display(self):
        """Display TRL improvement"""
        improvement = self.trl_improvement
        if improvement is None:
            return "Not specified"
        elif improvement > 0:
            return f"+{improvement} levels"
        elif improvement == 0:
            return "No change"
        else:
            return f"{improvement} levels"
    
    def get_raw_marks_total(self):
        """Get cached raw marks total"""
        return self.cached_raw_marks
    
    def get_max_possible_marks(self):
        """Get cached max possible marks"""
        return self.cached_max_marks
    
    def get_percentage_score(self):
        """Get cached percentage score"""
        return self.cached_percentage_score
    
    def check_and_update_completion_status(self):
        """AUTOMATIC completion detection - THIS IS THE KEY FIX"""
        try:
            # Get total expected criteria count
            if hasattr(self.evaluation_round, 'proposal') and hasattr(self.evaluation_round.proposal, 'service'):
                expected_criteria_count = self.evaluation_round.proposal.service.evaluationitem_set.filter(
                    status='Active', type='criteria'
                ).count()
            else:
                # Fallback: get unique criteria count from all evaluations in this round
                expected_criteria_count = CriteriaEvaluation.objects.filter(
                    evaluator_assignment__evaluation_round=self.evaluation_round
                ).values('evaluation_criteria').distinct().count()
            
            # Get this assignment's criteria count
            completed_criteria_count = self.criteria_evaluations.count()
            
            old_is_completed = self.is_completed
            
            # Auto-complete if all criteria are evaluated
            if expected_criteria_count > 0 and completed_criteria_count >= expected_criteria_count:
                self.is_completed = True
                if not self.completed_at:
                    self.completed_at = timezone.now()
            else:
                self.is_completed = False
                self.completed_at = None
            
            # Return True if completion status changed
            return old_is_completed != self.is_completed
            
        except Exception as e:
            logger.error(f"Error checking completion status for assignment {self.id}: {e}")
            return False
    
    def update_cached_values(self):
        """Update all cached values for this assignment - IMPROVED VERSION"""
        try:
            # Prevent recursive calls
            if hasattr(self, '_updating_cache'):
                return
            
            self._updating_cache = True
            
            # FIRST: Check and update completion status automatically
            completion_status_changed = self.check_and_update_completion_status()
            
            if self.is_completed:
                criteria_evaluations = self.criteria_evaluations.select_related('evaluation_criteria')
                
                if criteria_evaluations.exists():
                    # FORCE UPDATE each criteria's cache first
                    for ce in criteria_evaluations:
                        ce.update_cached_values()
                    
                    # Now calculate totals
                    raw_total = sum(float(ce.marks_given) for ce in criteria_evaluations)
                    max_total = sum(float(ce.evaluation_criteria.total_marks) for ce in criteria_evaluations)
                    
                    self.cached_raw_marks = raw_total
                    self.cached_max_marks = max_total
                    self.cached_percentage_score = round((raw_total / max_total) * 100, 2) if max_total > 0 else 0
                    self.cached_criteria_count = criteria_evaluations.count()
                    
                    # Cache criteria data
                    criteria_data = []
                    for ce in criteria_evaluations:
                        criteria_data.append({
                            'criteria_name': ce.evaluation_criteria.name,
                            'marks_given': float(ce.marks_given),
                            'max_marks': float(ce.evaluation_criteria.total_marks),
                            'percentage': ce.cached_percentage or 0,
                            'remarks': ce.remarks,
                        })
                    self.cached_criteria_data = criteria_data
                else:
                    self.cached_raw_marks = 0
                    self.cached_max_marks = 0
                    self.cached_percentage_score = 0
                    self.cached_criteria_count = 0
                    self.cached_criteria_data = []
            else:
                # Clear cache if not completed
                self.cached_raw_marks = None
                self.cached_max_marks = None
                self.cached_percentage_score = None
                self.cached_criteria_count = 0
                self.cached_criteria_data = None
            
            # Save with specific fields
            self.save(update_fields=[
                'is_completed',
                'completed_at',
                'cached_raw_marks', 
                'cached_max_marks', 
                'cached_percentage_score',
                'cached_criteria_count',
                'cached_criteria_data'
            ])
            
            logger.info(f"Updated cached values for assignment {self.id} - Completed: {self.is_completed}")
            
            # Remove the flag
            delattr(self, '_updating_cache')
            
            # If completion status changed, update evaluation round cache
            if completion_status_changed:
                self.evaluation_round.update_cached_values()
            
        except Exception as e:
            logger.error(f"Error updating cached values for assignment {self.id}: {e}")
            if hasattr(self, '_updating_cache'):
                delattr(self, '_updating_cache')
    
    def save(self, *args, **kwargs):
        """Override save to automatically check completion"""
        # Only auto-check completion if not already manually set
        if not kwargs.get('update_fields') or 'is_completed' not in kwargs.get('update_fields', []):
            self.check_and_update_completion_status()
        super().save(*args, **kwargs)


class CriteriaEvaluation(models.Model):
    """
    Individual criteria evaluation with cached calculations
    """
    evaluator_assignment = models.ForeignKey(
        EvaluatorAssignment,
        on_delete=models.CASCADE,
        related_name='criteria_evaluations',
        db_index=True
    )
    
    evaluation_criteria = models.ForeignKey(
        'app_eval.EvaluationItem',
        on_delete=models.CASCADE,
        related_name='tech_eval_criteria_evaluations',
        limit_choices_to={'status': 'Active', 'type': 'criteria'},
        db_index=True
    )
    
    marks_given = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Marks awarded for this criteria"
    )
    
    remarks = models.TextField(
        blank=True,
        help_text="Evaluator's remarks for this criteria"
    )
    
    # CACHED FIELDS for performance
    cached_percentage = models.FloatField(null=True, blank=True)
    cached_weighted_score = models.FloatField(null=True, blank=True)
    
    evaluated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        unique_together = ['evaluator_assignment', 'evaluation_criteria']
        ordering = ['evaluation_criteria__name']
        verbose_name = "Criteria Evaluation"
        verbose_name_plural = "Criteria Evaluations"
        indexes = [
            models.Index(fields=['evaluator_assignment', 'evaluation_criteria']),
            models.Index(fields=['evaluation_criteria', '-evaluated_at']),
        ]
    
    def __str__(self):
        criteria_name = getattr(self.evaluation_criteria, 'name', 'Unknown')
        total_marks = getattr(self.evaluation_criteria, 'total_marks', 0)
        return f"{criteria_name} - {self.marks_given}/{total_marks}"
    
    @property
    def percentage_score(self):
        """Get cached percentage score"""
        return self.cached_percentage or 0
    
    @property
    def weighted_score(self):
        """Get cached weighted score"""
        return self.cached_weighted_score or 0
    
    @property
    def marks_display(self):
        """Display marks in user-friendly format"""
        total_marks = getattr(self.evaluation_criteria, 'total_marks', 0)
        return f"{self.marks_given}/{total_marks} ({self.percentage_score}%)"
    
    def update_cached_values(self):
        """Update cached percentage and weighted score"""
        try:
            # Prevent recursive calls
            if hasattr(self, '_updating_criteria_cache'):
                return
                
            self._updating_criteria_cache = True
            
            if self.evaluation_criteria and self.evaluation_criteria.total_marks:
                total_marks = float(self.evaluation_criteria.total_marks)
                if total_marks > 0:
                    self.cached_percentage = round((float(self.marks_given) / total_marks) * 100, 2)
                    
                    # Calculate weighted score if weightage exists
                    weightage = getattr(self.evaluation_criteria, 'weightage', 0)
                    if weightage:
                        self.cached_weighted_score = round((self.cached_percentage / 100) * float(weightage), 2)
                    else:
                        self.cached_weighted_score = self.cached_percentage
            
            self.save(update_fields=['cached_percentage', 'cached_weighted_score'])
            
            # Remove the flag
            delattr(self, '_updating_criteria_cache')
            
        except Exception as e:
            logger.error(f"Error updating cached values for criteria evaluation {self.id}: {e}")
            if hasattr(self, '_updating_criteria_cache'):
                delattr(self, '_updating_criteria_cache')
    
    def clean(self):
        """Validate marks don't exceed maximum"""
        from django.core.exceptions import ValidationError
        
        if self.marks_given and self.evaluation_criteria:
            max_marks = float(self.evaluation_criteria.total_marks)
            if float(self.marks_given) > max_marks:
                raise ValidationError(
                    f"Marks given ({self.marks_given}) cannot exceed maximum marks ({max_marks}) for {self.evaluation_criteria.name}"
                )
            if float(self.marks_given) < 0:
                raise ValidationError("Marks cannot be negative")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

# IMPROVED SIGNALS - Less aggressive recursion prevention

@receiver(post_save, sender=CriteriaEvaluation)
def trigger_cache_update_on_criteria_save(sender, instance, created, **kwargs):
    """Trigger cache updates when criteria is saved"""
    def update_caches():
        try:
            # Update criteria cache
            instance.update_cached_values()
            
            # Update assignment cache (which will auto-check completion)
            if instance.evaluator_assignment:
                instance.evaluator_assignment.update_cached_values()
                
        except Exception as e:
            logger.error(f"Error in criteria save signal: {e}")
    
    # Use transaction.on_commit to ensure save is complete
    transaction.on_commit(update_caches)


@receiver(post_delete, sender=CriteriaEvaluation)
def trigger_cache_update_on_criteria_delete(sender, instance, **kwargs):
    """Trigger cache updates when criteria is deleted"""
    def update_caches():
        try:
            # Update assignment cache (which will auto-check completion)
            if instance.evaluator_assignment:
                instance.evaluator_assignment.update_cached_values()
                
        except Exception as e:
            logger.error(f"Error in criteria delete signal: {e}")
    
    transaction.on_commit(update_caches)


@receiver(post_save, sender=EvaluatorAssignment)
def trigger_round_cache_update_on_assignment_save(sender, instance, created, **kwargs):
    """Update round cache when assignment changes"""
    def update_round_cache():
        try:
            if instance.evaluation_round:
                instance.evaluation_round.update_cached_values()
        except Exception as e:
            logger.error(f"Error in assignment save signal: {e}")
    
    # Only update if not in the middle of updating assignment cache
    if not hasattr(instance, '_updating_cache'):
        transaction.on_commit(update_round_cache)


@receiver(post_delete, sender=EvaluatorAssignment)
def trigger_round_cache_update_on_assignment_delete(sender, instance, **kwargs):
    """Update round cache when assignment is deleted"""
    def update_round_cache():
        try:
            if instance.evaluation_round:
                instance.evaluation_round.update_cached_values()
        except Exception as e:
            logger.error(f"Error in assignment delete signal: {e}")
    
    transaction.on_commit(update_round_cache)


# Additional models for audit and performance tracking

class EvaluationAuditLog(models.Model):
    """
    Audit log for tracking evaluation changes
    """
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('completed', 'Completed'),
        ('assigned', 'Assigned'),
        ('decision_made', 'Decision Made'),
        ('cache_updated', 'Cache Updated'),
    ]
    
    evaluation_round = models.ForeignKey(
        TechnicalEvaluationRound,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        db_index=True
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    description = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Evaluation Audit Log"
        verbose_name_plural = "Evaluation Audit Logs"
        indexes = [
            models.Index(fields=['evaluation_round', '-created_at']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        user_name = str(self.user) if self.user else 'System'
        return f"{self.action} - {self.evaluation_round} by {user_name}"


class TRLAnalysis(models.Model):
    """
    TRL analysis with cached calculations
    """
    evaluation_round = models.OneToOneField(
        TechnicalEvaluationRound,
        on_delete=models.CASCADE,
        related_name='trl_analysis',
        db_index=True
    )
    
    consensus_current_trl = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(9)]
    )
    
    consensus_expected_trl = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(9)]
    )
    
    trl_variance = models.FloatField(null=True, blank=True)
    
    trl_consensus_level = models.CharField(
        max_length=10,
        choices=[
            ('high', 'High Consensus'),
            ('medium', 'Medium Consensus'),
            ('low', 'Low Consensus'),
        ],
        null=True,
        blank=True,
        db_index=True
    )
    
    analysis_notes = models.TextField(blank=True)
    cached_analysis_summary = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "TRL Analysis"
        verbose_name_plural = "TRL Analyses"
        indexes = [
            models.Index(fields=['trl_consensus_level', '-created_at']),
            models.Index(fields=['consensus_expected_trl']),
        ]
    
    def __str__(self):
        return f"TRL Analysis - {self.evaluation_round}"
    
    def calculate_consensus(self):
        """Calculate TRL consensus from completed evaluations"""
        assignments = self.evaluation_round.evaluator_assignments.filter(
            is_completed=True,
            expected_trl__isnull=False
        ).values_list('expected_trl', flat=True)
        
        if len(assignments) < 2:
            return
        
        expected_trls = list(assignments)
        mean_trl = sum(expected_trls) / len(expected_trls)
        variance = sum((trl - mean_trl) ** 2 for trl in expected_trls) / len(expected_trls)
        
        self.trl_variance = variance
        self.consensus_expected_trl = round(mean_trl)
        
        # Determine consensus level
        if variance <= 0.5:
            self.trl_consensus_level = 'high'
        elif variance <= 1.5:
            self.trl_consensus_level = 'medium'
        else:
            self.trl_consensus_level = 'low'
        
        # Cache analysis summary
        self.cached_analysis_summary = {
            'mean_trl': mean_trl,
            'variance': variance,
            'consensus_level': self.trl_consensus_level,
            'total_evaluators': len(expected_trls),
            'trl_distribution': {str(trl): expected_trls.count(trl) for trl in set(expected_trls)}
        }
        
        self.save()