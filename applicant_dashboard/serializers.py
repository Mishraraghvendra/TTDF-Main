# applicant_dashboard/serializers.py

from rest_framework import serializers
from .models import DashboardStats, UserActivity, DraftApplication
from dynamic_form.models import FormSubmission


class DashboardStatsSerializer(serializers.ModelSerializer):
    """Serializer for dashboard statistics"""
    
    class Meta:
        model = DashboardStats
        fields = [
            'total_proposals',
            'approved_proposals', 
            'under_evaluation',
            'not_shortlisted',
            'draft_applications',
            'last_updated'
        ]


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activities and notifications"""
    time_ago = serializers.ReadOnlyField()
    
    class Meta:
        model = UserActivity
        fields = [
            'id',
            'activity_type',
            'title', 
            'description',
            'is_read',
            'time_ago',
            'created_at'
        ]


class DraftApplicationSerializer(serializers.ModelSerializer):
    """Serializer for draft applications"""
    call_title = serializers.SerializerMethodField()
    application_no = serializers.SerializerMethodField()
    
    class Meta:
        model = DraftApplication
        fields = [
            'id',
            'call_title',
            'application_no', 
            'progress_percentage',
            'last_section_completed',
            'last_updated'
        ]
    
    def get_call_title(self, obj):
        """Get the call/service name"""
        if obj.submission and obj.submission.service:
            return obj.submission.service.name
        return 'Unknown Call'
    
    def get_application_no(self, obj):
        """Get the application/proposal ID"""
        if obj.submission and obj.submission.proposal_id:
            return obj.submission.proposal_id
        elif obj.submission and obj.submission.form_id:
            return obj.submission.form_id
        return 'Draft'


class ProposalSummarySerializer(serializers.ModelSerializer):
    """Serializer for recent proposals summary"""
    service_name = serializers.SerializerMethodField()
    
    class Meta:
        model = FormSubmission
        fields = [
            'proposal_id',
            'form_id',
            'service_name',
            'status',
            'created_at',
            'updated_at'
        ]
    
    def get_service_name(self, obj):
        """Get service name if available"""
        if obj.service:
            return obj.service.name
        return 'General Application'


class CallDataSerializer(serializers.Serializer):
    """Serializer for call data from Service model"""
    title = serializers.CharField()
    description = serializers.CharField()
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True) 
    posted_date = serializers.CharField()
    status = serializers.CharField()


class ProposalStatsSerializer(serializers.Serializer):
    """Serializer for proposal statistics by category"""
    title = serializers.CharField()
    proposalId = serializers.CharField()
    status = serializers.CharField()
    date = serializers.CharField()
    remarks = serializers.CharField()
    daysPending = serializers.IntegerField()
    requiredDocuments = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )