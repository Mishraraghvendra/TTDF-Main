# tech_eval/serializers.py - 

from rest_framework import serializers
from .models import TechnicalEvaluationRound, EvaluatorAssignment, CriteriaEvaluation
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class LightningFastCriteriaEvaluationSerializer(serializers.ModelSerializer):
    """Ultra-fast criteria evaluation serializer using cached fields"""
    criteria_name = serializers.CharField(source='evaluation_criteria.name', read_only=True)
    max_marks = serializers.DecimalField(source='evaluation_criteria.total_marks', max_digits=5, decimal_places=2, read_only=True)
    percentage_score = serializers.FloatField(source='cached_percentage', read_only=True)  # CACHED!
    weighted_score = serializers.FloatField(source='cached_weighted_score', read_only=True)  # CACHED!
    
    class Meta:
        model = CriteriaEvaluation
        fields = [
            'id', 'criteria_name', 'marks_given', 'max_marks', 
            'percentage_score', 'weighted_score', 'remarks', 'evaluated_at'
        ]

class LightningFastEvaluatorAssignmentSerializer(serializers.ModelSerializer):
    """Ultra-fast evaluator assignment serializer using cached fields"""
    evaluator_name = serializers.CharField(source='evaluator.get_full_name', read_only=True)
    evaluator_email = serializers.CharField(source='evaluator.email', read_only=True)
    
    # FIXED: Add the missing evaluation_round field
    evaluation_round = serializers.IntegerField(source='evaluation_round_id', read_only=True)
    
    # Use CACHED fields for performance
    raw_marks_total = serializers.FloatField(source='cached_raw_marks', read_only=True)
    max_possible_marks = serializers.FloatField(source='cached_max_marks', read_only=True)
    percentage_score = serializers.FloatField(source='cached_percentage_score', read_only=True)
    criteria_count = serializers.IntegerField(source='cached_criteria_count', read_only=True)
    
    # Include cached criteria data instead of live queries
    criteria_evaluations = serializers.SerializerMethodField()
    
    class Meta:
        model = EvaluatorAssignment
        fields = [
            'id', 'evaluation_round', 'evaluator_name', 'evaluator_email', 'is_completed',  # Added evaluation_round
            'expected_trl', 'conflict_of_interest', 'conflict_remarks', 'overall_comments',
            'raw_marks_total', 'max_possible_marks', 'percentage_score', 'criteria_count',
            'criteria_evaluations', 'assigned_at', 'completed_at'
        ]
    
    def get_criteria_evaluations(self, obj):
        """Use cached criteria data for lightning speed"""
        if obj.cached_criteria_data:
            return obj.cached_criteria_data
        return []

class LightningFastTechnicalEvaluationRoundSerializer(serializers.ModelSerializer):
    """Ultra-fast technical evaluation round serializer using cached fields"""
    proposal_id = serializers.SerializerMethodField()
    call = serializers.SerializerMethodField()
    
    # Use CACHED fields exclusively
    assigned_evaluators_count = serializers.IntegerField(source='cached_assigned_count', read_only=True)
    completed_evaluations_count = serializers.IntegerField(source='cached_completed_count', read_only=True)
    average_percentage = serializers.FloatField(source='cached_average_percentage', read_only=True)
    evaluation_marks_summary = serializers.JSONField(source='cached_marks_summary', read_only=True)
    assigned_evaluators = serializers.JSONField(source='cached_evaluator_data', read_only=True)
    
    # Computed fields using cached data
    is_all_evaluations_completed = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = TechnicalEvaluationRound
        fields = [
            'id', 'proposal_id', 'assignment_status', 'overall_decision',
            'assigned_evaluators_count', 'completed_evaluations_count', 'average_percentage',
            'evaluation_marks_summary', 'assigned_evaluators', 'is_all_evaluations_completed',
            'progress_percentage', 'created_at', 'completed_at'
        ]
    
    def get_proposal_id(self, obj):
        """Get proposal ID from cached data or direct field"""
        if obj.cached_proposal_data:
            return obj.cached_proposal_data.get('proposal_id')
        return obj.proposal.proposal_id if obj.proposal else None
    
    def get_is_all_evaluations_completed(self, obj):
        """Use cached counts for completion check"""
        return obj.cached_assigned_count > 0 and obj.cached_assigned_count == obj.cached_completed_count
    
    def get_progress_percentage(self, obj):
        """Calculate progress using cached counts"""
        if obj.cached_assigned_count == 0:
            return 0
        return round((obj.cached_completed_count / obj.cached_assigned_count) * 100, 1)
    
    def get_call(self, obj):
        # 1. Try from cache if exists
        if obj.cached_proposal_data and 'call' in obj.cached_proposal_data:
            return obj.cached_proposal_data.get('call') or 'N/A'
        # 2. Fallback: Directly from proposal.service.name
        try:
            proposal = obj.proposal
            if proposal and getattr(proposal, 'service', None):
                name = getattr(proposal.service, 'name', None)
                return name if name else 'N/A'
        except Exception:
            pass
        return 'N/A'


class SuperFastAdminListSerializer(serializers.ModelSerializer):
    """Lightning-fast admin list serializer using ONLY cached data"""
    
    # Use cached proposal data
    proposal_id = serializers.SerializerMethodField()
    call = serializers.SerializerMethodField()
    orgType = serializers.SerializerMethodField()
    orgName = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    contactPerson = serializers.SerializerMethodField()
    contactEmail = serializers.SerializerMethodField()
    contactPhone = serializers.SerializerMethodField()
    
    # Use cached evaluation data
    assigned_evaluators_count = serializers.IntegerField(source='cached_assigned_count', read_only=True)
    completed_evaluations_count = serializers.IntegerField(source='cached_completed_count', read_only=True)
    evaluation_marks_summary = serializers.JSONField(source='cached_marks_summary', read_only=True)
    assigned_evaluators = serializers.JSONField(source='cached_evaluator_data', read_only=True)
    
    # Computed fields
    submissionDate = serializers.DateTimeField(source='created_at', read_only=True)
    completed_evaluations = serializers.SerializerMethodField()
    
    class Meta:
        model = TechnicalEvaluationRound
        fields = [
            'id', 'proposal_id', 'call', 'orgType', 'orgName', 'subject', 'description',
            'contactPerson', 'contactEmail', 'contactPhone', 'submissionDate',
            'assignment_status', 'overall_decision', 'assigned_evaluators_count', 
            'completed_evaluations_count', 'evaluation_marks_summary', 
            'assigned_evaluators', 'completed_evaluations'
        ]
    
    def get_proposal_id(self, obj):
        if obj.cached_proposal_data:
            return obj.cached_proposal_data.get('proposal_id')
        return obj.proposal.proposal_id if obj.proposal else None
    
    def get_call(self, obj):
        if obj.cached_proposal_data:
            return obj.cached_proposal_data.get('call', 'N/A')
        # Fallback to parsing form_data
        if obj.proposal and hasattr(obj.proposal, 'form_data'):
            try:
                form_data = json.loads(obj.proposal.form_data) if isinstance(obj.proposal.form_data, str) else obj.proposal.form_data
                return form_data.get('call_name', 'N/A')
            except:
                pass
        return 'N/A'
    
    def get_orgType(self, obj):
        if obj.cached_proposal_data:
            return obj.cached_proposal_data.get('org_type', 'N/A')
        if obj.proposal and hasattr(obj.proposal, 'form_data'):
            try:
                form_data = json.loads(obj.proposal.form_data) if isinstance(obj.proposal.form_data, str) else obj.proposal.form_data
                return form_data.get('organization_type', 'N/A')
            except:
                pass
        return 'N/A'
    
    def get_orgName(self, obj):
        if obj.cached_proposal_data:
            return obj.cached_proposal_data.get('org_name', 'N/A')
        return obj.proposal.applicant.organization if obj.proposal and obj.proposal.applicant else 'N/A'
    
    def get_subject(self, obj):
        if obj.cached_proposal_data:
            return obj.cached_proposal_data.get('subject', 'N/A')
        if obj.proposal and hasattr(obj.proposal, 'form_data'):
            try:
                form_data = json.loads(obj.proposal.form_data) if isinstance(obj.proposal.form_data, str) else obj.proposal.form_data
                return form_data.get('project_title', 'N/A')
            except:
                pass
        return 'N/A'
    
    def get_description(self, obj):
        if obj.cached_proposal_data:
            desc = obj.cached_proposal_data.get('description', 'N/A')
            return desc[:200] + ('...' if len(desc) > 200 else '')
        if obj.proposal and hasattr(obj.proposal, 'form_data'):
            try:
                form_data = json.loads(obj.proposal.form_data) if isinstance(obj.proposal.form_data, str) else obj.proposal.form_data
                desc = form_data.get('project_description', 'N/A')
                return desc[:200] + ('...' if len(desc) > 200 else '')
            except:
                pass
        return 'N/A'
    
    def get_contactPerson(self, obj):
        if obj.cached_proposal_data:
          return obj.cached_proposal_data.get('contact_person', 'N/A')
        if obj.proposal and obj.proposal.applicant:
           applicant = obj.proposal.applicant
           return getattr(applicant, 'full_name', 'N/A')
        return 'N/A'

    
    def get_contactEmail(self, obj):
        if obj.cached_proposal_data:
            return obj.cached_proposal_data.get('contact_email', 'N/A')
        return obj.proposal.applicant.email if obj.proposal and obj.proposal.applicant else 'N/A'
    
    def get_contactPhone(self, obj):
        if obj.cached_proposal_data:
           return obj.cached_proposal_data.get('contact_phone', 'N/A')
        return getattr(obj.proposal.applicant, 'mobile', 'N/A') if obj.proposal and obj.proposal.applicant else 'N/A'
    
    def get_completed_evaluations(self, obj):
        """Filter completed evaluations from cached data"""
        if obj.cached_evaluator_data:
            return [e for e in obj.cached_evaluator_data if e.get('is_completed')]
        return []

class FastEvaluatorUserSerializer(serializers.ModelSerializer):
    """Fast evaluator user serializer"""
    name = serializers.CharField(source='get_full_name', read_only=True)
    mobile = serializers.CharField(source='mobile', read_only=True)  # Changed from 'phone' to 'mobile'
    
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'mobile']
    
    def to_representation(self, instance):
        """Custom fast serialization"""
        return {
            'id': instance.id,
            'name': instance.get_full_name() if hasattr(instance, 'get_full_name') else getattr(instance, 'full_name', 'Unknown'),
            'email': getattr(instance, 'email', ''),
            'mobile': getattr(instance, 'mobile', 'N/A'),  # Changed from 'phone' to 'mobile'
            'specialization': 'Technical Expert',
            'profile': {
                'specialization': 'Technical Expert'
            }
        }
class FastAppEvalCriteriaSerializer(serializers.ModelSerializer):
    """Ultra-fast criteria serializer"""
    
    class Meta:
        fields = ['id', 'name', 'description', 'total_marks', 'weightage', 'status', 'type']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app_eval.models import EvaluationItem
        self.Meta.model = EvaluationItem
    
    def to_representation(self, instance):
        """Custom fast serialization"""
        return {
            'id': instance.id,
            'name': instance.name,
            'description': getattr(instance, 'description', ''),
            'total_marks': instance.total_marks,
            'weightage': getattr(instance, 'weightage', 0),
            'status': 'Active',
            'type': 'criteria'
        }

# Specialized serializers for different use cases

class DashboardStatsSerializer(serializers.Serializer):
    """Ultra-fast dashboard statistics using cached fields"""
    total_proposals = serializers.IntegerField()
    pending_assignments = serializers.IntegerField()
    in_evaluation = serializers.IntegerField()
    completed_evaluations = serializers.IntegerField()
    recommended = serializers.IntegerField()
    not_recommended = serializers.IntegerField()
    average_completion_rate = serializers.FloatField()

class QuickSearchResultSerializer(serializers.Serializer):
    """Quick search results using cached data"""
    id = serializers.IntegerField()
    proposal_id = serializers.CharField()
    subject = serializers.CharField()
    organization = serializers.CharField()
    status = serializers.CharField()
    progress_percentage = serializers.FloatField()
    last_updated = serializers.DateTimeField()

class EvaluationSummarySerializer(serializers.Serializer):
    """Fast evaluation summary using cached data"""
    evaluation_round_id = serializers.IntegerField()
    proposal_id = serializers.CharField()
    total_evaluators = serializers.IntegerField()
    completed_evaluators = serializers.IntegerField()
    average_percentage = serializers.FloatField()
    decision_status = serializers.CharField()
    marks_summary = serializers.JSONField()
    evaluator_details = serializers.JSONField()

# Optimized detail serializers (when full data is needed)

class DetailedEvaluationRoundSerializer(serializers.ModelSerializer):
    """Use only when full details are required - still optimized with cached fields"""
    
    # Use cached fields for performance
    assigned_evaluators_count = serializers.IntegerField(source='cached_assigned_count', read_only=True)
    completed_evaluations_count = serializers.IntegerField(source='cached_completed_count', read_only=True)
    average_percentage = serializers.FloatField(source='cached_average_percentage', read_only=True)
    evaluation_marks_summary = serializers.JSONField(source='cached_marks_summary', read_only=True)
    
    # Conditionally include expensive fields
    assigned_evaluators = serializers.SerializerMethodField()
    completed_evaluations = serializers.SerializerMethodField()
    proposal_details = serializers.SerializerMethodField()
    
    class Meta:
        model = TechnicalEvaluationRound
        fields = [
            'id', 'assignment_status', 'overall_decision', 'created_at', 'completed_at',
            'assigned_evaluators_count', 'completed_evaluations_count', 'average_percentage',
            'evaluation_marks_summary', 'assigned_evaluators', 'completed_evaluations',
            'proposal_details'
        ]
    
    def get_assigned_evaluators(self, obj):
        """Use cached evaluator data if available"""
        request = self.context.get('request')
        include_fields = request.GET.get('include', '').split(',') if request else []
        
        if 'evaluators' in include_fields:
            return obj.cached_evaluator_data or []
        return []
    
    def get_completed_evaluations(self, obj):
        """Filter completed from cached data"""
        request = self.context.get('request')
        include_fields = request.GET.get('include', '').split(',') if request else []
        
        if 'evaluations' in include_fields and obj.cached_evaluator_data:
            return [e for e in obj.cached_evaluator_data if e.get('is_completed')]
        return []
    
    def get_proposal_details(self, obj):
        """Use cached proposal data if available"""
        request = self.context.get('request')
        include_fields = request.GET.get('include', '').split(',') if request else []
        
        if 'proposal' in include_fields:
            return obj.cached_proposal_data or {}
        return {}

# Bulk operation serializers

class BulkAssignmentSerializer(serializers.Serializer):
    """For bulk evaluator assignments"""
    evaluation_round_ids = serializers.ListField(child=serializers.IntegerField())
    evaluator_ids = serializers.ListField(child=serializers.IntegerField())

class BulkDecisionSerializer(serializers.Serializer):
    """For bulk decision making"""
    evaluation_round_ids = serializers.ListField(child=serializers.IntegerField())
    decision = serializers.ChoiceField(choices=['recommended', 'not_recommended'])

# Export serializers

class ExcelExportSerializer(serializers.Serializer):
    """For Excel export functionality"""
    include_evaluations = serializers.BooleanField(default=False)
    include_comments = serializers.BooleanField(default=False)
    include_marks_breakdown = serializers.BooleanField(default=False)
    date_range_start = serializers.DateField(required=False)
    date_range_end = serializers.DateField(required=False)
    status_filter = serializers.ChoiceField(
        choices=['all', 'pending', 'assigned', 'completed'],
        default='all'
    )

# Error and success response serializers

class ErrorResponseSerializer(serializers.Serializer):
    """Standardized error responses"""
    error = serializers.CharField()
    detail = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    timestamp = serializers.DateTimeField(required=False)

class SuccessResponseSerializer(serializers.Serializer):
    """Standardized success responses"""
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = serializers.JSONField(required=False)
    timestamp = serializers.DateTimeField(required=False)

# Performance monitoring serializers

class PerformanceMetricSerializer(serializers.Serializer):
    """For tracking API performance"""
    endpoint = serializers.CharField()
    method = serializers.CharField()
    response_time_ms = serializers.IntegerField()
    query_count = serializers.IntegerField()
    cached_fields_used = serializers.BooleanField()
    cache_hit_rate = serializers.FloatField()

# Cache status serializers

class CacheStatusSerializer(serializers.Serializer):
    """For monitoring cache status"""
    model_name = serializers.CharField()
    total_records = serializers.IntegerField()
    cached_records = serializers.IntegerField()
    cache_hit_rate = serializers.FloatField()
    last_cache_update = serializers.DateTimeField()
    cache_size_mb = serializers.FloatField()



class CacheUpdateSerializer(serializers.Serializer):
    """For cache update operations"""
    model_type = serializers.ChoiceField(
        choices=['evaluation_rounds', 'assignments', 'criteria_evaluations', 'all']
    )
    force_update = serializers.BooleanField(default=False)
    batch_size = serializers.IntegerField(default=100)

class MaintenanceStatusSerializer(serializers.Serializer):
    """For system maintenance status"""
    cache_health = serializers.CharField()
    database_performance = serializers.CharField()
    average_response_time = serializers.FloatField()
    total_cached_records = serializers.IntegerField()
    last_maintenance = serializers.DateTimeField()
    recommendations = serializers.ListField(child=serializers.CharField())
    
    