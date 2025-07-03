# proposal_aggregate/api/serializers.py
from rest_framework import serializers
from dynamic_form.models import FormSubmission, FieldResponse, ApplicationStatusHistory
from app_eval.models import (
    EvaluationAssignment, CriteriaEvaluation as AppEvalCriteriaEvaluation,
    QuestionEvaluation, EvaluationCutoff
)
from configuration.models import (
    Application as ConfigApplication,
    ApplicationStageProgress, ScreeningResult
)
from milestones.models import Milestone, SubMilestone, FinanceRequest, PaymentClaim, FinanceSanction
from presentation.models import Presentation
from screening.models import ScreeningRecord, TechnicalScreeningRecord
from tech_eval.models import TechnicalEvaluationRound, CriteriaEvaluation as TechEvalCriteriaEvaluation

# --- Nested Serializers ---
class FieldResponseSerializer(serializers.ModelSerializer):
    field_label = serializers.CharField(source='field.label', read_only=True)

    class Meta:
        model = FieldResponse
        fields = ['id', 'field', 'field_label', 'value']

class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationStatusHistory
        fields = ['previous_status', 'new_status', 'changed_by', 'change_date', 'comment']

# Configuration nested
class ApplicationStageProgressSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source='stage.name', read_only=True)

    class Meta:
        model = ApplicationStageProgress
        fields = ['id', 'stage', 'stage_name', 'status', 'start_date', 'completion_date', 'total_score']

class ScreeningResultSerializer(serializers.ModelSerializer):
    committee_name = serializers.CharField(source='committee.name', read_only=True)

    class Meta:
        model = ScreeningResult
        fields = ['id', 'committee', 'committee_name', 'result', 'notes', 'screened_by', 'screened_at']

class ConfigApplicationSerializer(serializers.ModelSerializer):
    stage_progress = ApplicationStageProgressSerializer(many=True, read_only=True)
    screening_results = ScreeningResultSerializer(many=True, read_only=True)

    class Meta:
        model = ConfigApplication
        fields = ['id', 'service', 'status', 'submitted_at', 'current_stage', 'stage_progress', 'screening_results']

# AppEval nested
class AppEvalCriteriaEvaluationSerializer(serializers.ModelSerializer):
    criteria_name = serializers.CharField(source='criteria.name', read_only=True)

    class Meta:
        model = AppEvalCriteriaEvaluation
        fields = ['criteria', 'criteria_name', 'marks_given', 'comments', 'date_evaluated']

class QuestionEvaluationSerializer(serializers.ModelSerializer):
    question_name = serializers.CharField(source='question.name', read_only=True)

    class Meta:
        model = QuestionEvaluation
        fields = ['question', 'question_name', 'marks_given', 'comments', 'date_evaluated']

class EvaluationAssignmentSerializer(serializers.ModelSerializer):
    evaluator_email = serializers.EmailField(source='evaluator.email', read_only=True)
    criteria_evaluations = AppEvalCriteriaEvaluationSerializer(many=True, read_only=True)
    question_evaluations = QuestionEvaluationSerializer(many=True, read_only=True)

    class Meta:
        model = EvaluationAssignment
        fields = [
            'evaluator', 'evaluator_email', 'current_trl', 'expected_trl',
            'remarks', 'conflict_of_interest', 'conflict_remarks',
            'total_marks_assigned', 'evaluated_at',
            'criteria_evaluations', 'question_evaluations',
        ]

class EvaluationCutoffSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationCutoff
        fields = ['cutoff_marks']

# Milestones nested
class SubMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubMilestone
        fields = '__all__'

class FinanceSanctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceSanction
        fields = ['sanction_date', 'sanction_amount', 'sanction_note', 'status', 'jf_user', 'reviewed_at']

class PaymentClaimSerializer(serializers.ModelSerializer):
    finance_sanction = FinanceSanctionSerializer(read_only=True)

    class Meta:
        model = PaymentClaim
        fields = ['status', 'advance_payment', 'penalty_amount', 'adjustment_amount', 'reviewed_at', 'finance_sanction']

class FinanceRequestSerializer(serializers.ModelSerializer):
    payment_claim = PaymentClaimSerializer(read_only=True)

    class Meta:
        model = FinanceRequest
        fields = ['id', 'status', 'ia_remark', 'reviewed_at', 'payment_claim']

class MilestoneSerializer(serializers.ModelSerializer):
    submilestones = SubMilestoneSerializer(many=True, read_only=True)
    finance_requests = FinanceRequestSerializer(many=True, read_only=True)

    class Meta:
        model = Milestone
        fields = [
            'title', 'time_required', 'revised_time_required',
            'grant_from_ttdf', 'description', 'submilestones', 'finance_requests'
        ]

# Presentation nested
class PresentationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Presentation
        fields = [
            'video', 'document', 'presentation_date',
            'evaluator_marks', 'evaluator_remarks',
            'final_decision', 'admin_remarks'
        ]

# Screening nested
class TechnicalScreeningRecordSerializer(serializers.ModelSerializer):
    technical_evaluator_email = serializers.EmailField(source='technical_evaluator.email', read_only=True)

    class Meta:
        model = TechnicalScreeningRecord
        fields = [
            'technical_evaluator', 'technical_evaluator_email',
            'technical_decision', 'technical_marks', 'technical_remarks',
            'technical_screened_at'
        ]

class ScreeningRecordSerializer(serializers.ModelSerializer):
    admin_evaluator_email = serializers.EmailField(source='admin_evaluator.email', read_only=True)
    technical_record = TechnicalScreeningRecordSerializer(read_only=True)

    class Meta:
        model = ScreeningRecord
        fields = [
            'cycle', 'admin_evaluator', 'admin_evaluator_email',
            'admin_decision', 'admin_remarks', 'admin_screened_at',
            'technical_evaluated', 'technical_record'
        ]

# Technical Evaluations nested
class TechEvalCriteriaEvaluationSerializer(serializers.ModelSerializer):
    criteria_name = serializers.CharField(source='evaluation_criteria.name', read_only=True)

    class Meta:
        model = TechEvalCriteriaEvaluation
        fields = ['evaluation_criteria', 'criteria_name', 'marks_given', 'remarks', 'evaluated_at']

class TechnicalEvaluationRoundSerializer(serializers.ModelSerializer):
    criteria_evaluations = TechEvalCriteriaEvaluationSerializer(many=True, read_only=True)

    class Meta:
        model = TechnicalEvaluationRound
        fields = [
            'evaluated_by', 'technical_comments', 'technical_decision',
            'evaluated_at', 'criteria_evaluations'
        ]

# Master Serializer
class ProposalDetailSerializer(serializers.ModelSerializer):
    responses = FieldResponseSerializer(many=True, read_only=True)
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)
    applications = ConfigApplicationSerializer(many=True, read_only=True)
    eval_assignments = EvaluationAssignmentSerializer(many=True, read_only=True)
    eval_cutoff = EvaluationCutoffSerializer(read_only=True)
    screening_records = ScreeningRecordSerializer(many=True, read_only=True)
    technical_evaluations = TechnicalEvaluationRoundSerializer(many=True, read_only=True)
    presentations = PresentationSerializer(many=True, read_only=True)
    milestones = MilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = FormSubmission
        fields = [
            'form_id', 'proposal_id', 'status', 'contact_name', 'contact_email',
            'created_at', 'updated_at',
            'responses', 'status_history', 'applications',
            'eval_assignments', 'eval_cutoff',
            'screening_records', 'technical_evaluations',
            'presentations', 'milestones'
        ]
