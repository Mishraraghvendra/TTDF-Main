# presentation/serializers.py
from rest_framework import serializers
from .models import Presentation
from tech_eval.models import TechnicalEvaluationRound
from dynamic_form.models import FormSubmission
from configuration.models import ScreeningCommittee
from screening.models import ScreeningRecord
from app_eval.models import EvaluationAssignment
import logging
logger = logging.getLogger(__name__)
import time
 
class PresentationSerializer(serializers.ModelSerializer):
    # Read-only computed fields
    proposal_id = serializers.CharField(source='proposal.proposal_id', read_only=True)
    applicant_name = serializers.CharField(source='applicant.get_full_name', read_only=True)
    evaluator_name = serializers.CharField(source='evaluator.get_full_name', read_only=True)
    admin_name = serializers.CharField(source='admin.get_full_name', read_only=True)
   
    # Status checks
    is_ready_for_evaluation = serializers.BooleanField(read_only=True)
    is_evaluation_completed = serializers.BooleanField(read_only=True)
    can_make_final_decision = serializers.BooleanField(read_only=True)
 
    class Meta:
        model = Presentation
        fields = [
            'id', 'proposal', 'proposal_id', 'applicant', 'applicant_name',
            'video', 'document', 'presentation_date', 'document_uploaded',
            'created_at', 'updated_at',
            'evaluator', 'evaluator_name', 'evaluator_marks', 'evaluator_remarks', 'evaluated_at',
            'final_decision', 'admin_remarks', 'admin', 'admin_name', 'admin_evaluated_at',
            'is_ready_for_evaluation', 'is_evaluation_completed', 'can_make_final_decision'
        ]
        read_only_fields = [
            'id', 'proposal_id', 'applicant_name', 'evaluator_name', 'admin_name',
            'created_at', 'updated_at', 'document_uploaded', 'evaluated_at', 'admin_evaluated_at',
            'is_ready_for_evaluation', 'is_evaluation_completed', 'can_make_final_decision'
        ]
 
    def validate_evaluator_marks(self, value):
        """Validate evaluator marks are within acceptable range"""
        if value is not None:
            # Get max marks from passing requirements or default to 50
            try:
                from app_eval.models import PassingRequirement
                requirement = PassingRequirement.objects.filter(status='Active').first()
                max_marks = requirement.presentation_max_marks if requirement else 50
            except:
                max_marks = 50
           
            if value < 0 or value > max_marks:
                raise serializers.ValidationError(f"Marks must be between 0 and {max_marks}")
        return value
 
    def validate_final_decision(self, value):
        """Validate final decision transitions"""
        if self.instance and value in ['shortlisted', 'rejected']:
            if not self.instance.is_evaluation_completed:
                raise serializers.ValidationError(
                    "Cannot make final decision before evaluation is completed"
                )
        return value
 
 
class AdminPresentationListSerializer(serializers.ModelSerializer):
    """Serializer for admin list view of presentations"""
    proposal_id = serializers.CharField(source='proposal.proposal_id', read_only=True)
    proposal_subject = serializers.CharField(source='proposal.subject', read_only=True)
    applicant_name = serializers.CharField(source='applicant.get_full_name', read_only=True)
    applicant_email = serializers.EmailField(source='applicant.email', read_only=True)
    evaluator_name = serializers.CharField(source='evaluator.get_full_name', read_only=True)
    org_name = serializers.SerializerMethodField()
    funds_requested = serializers.SerializerMethodField()
   
    # Status indicators
    materials_uploaded = serializers.BooleanField(source='document_uploaded', read_only=True)
    evaluation_status = serializers.SerializerMethodField()
 
    class Meta:
        model = Presentation
        fields = [
            'id', 'proposal_id', 'proposal_subject', 'applicant_name', 'applicant_email',
            'org_name', 'funds_requested', 'evaluator_name',
            'final_decision', 'materials_uploaded', 'evaluation_status',
            'evaluator_marks', 'presentation_date', 'created_at'
        ]
 
    def get_org_name(self, obj):
        return getattr(obj.applicant, 'organization', '') or ''
 
    def get_funds_requested(self, obj):
        latest = obj.proposal.milestones.order_by('-created_at').first()
        return latest.funds_requested if latest else None
 
    def get_evaluation_status(self, obj):
        if obj.is_evaluation_completed:
            return "Completed"
        elif obj.is_ready_for_evaluation:
            return "Ready for Evaluation"
        elif obj.evaluator:
            return "Waiting for Materials"
        else:
            return "No Evaluator Assigned"
 
  
class EvaluatorPresentationSerializer(serializers.ModelSerializer):
    """Serializer for evaluator view of presentations"""
    proposal_id = serializers.CharField(source='proposal.proposal_id', read_only=True)
    proposal_subject = serializers.CharField(source='proposal.subject', read_only=True)
    proposal_description = serializers.CharField(source='proposal.description', read_only=True)
    applicant_name = serializers.CharField(source='applicant.get_full_name', read_only=True)
    applicant_email = serializers.EmailField(source='applicant.email', read_only=True)
    org_name = serializers.SerializerMethodField()
   
    # Max marks for reference
    max_marks = serializers.SerializerMethodField()
 
    class Meta:
        model = Presentation
        fields = [
            'id', 'proposal_id', 'proposal_subject', 'proposal_description',
            'applicant_name', 'applicant_email', 'org_name',
            'video', 'video_link', 'document', 'presentation_date',
            'evaluator_marks', 'evaluator_remarks', 'evaluated_at',
            'final_decision', 'max_marks', 'is_ready_for_evaluation',
            'is_evaluation_completed', 'document_uploaded'
        ]
        read_only_fields = [
            'proposal_id', 'proposal_subject', 'proposal_description',
            'applicant_name', 'applicant_email', 'org_name',
            'video', 'video_link', 'document', 'presentation_date', 'evaluated_at',
            'final_decision', 'max_marks', 'is_ready_for_evaluation',
            'is_evaluation_completed', 'document_uploaded'
        ]
 
    def get_org_name(self, obj):
        return getattr(obj.applicant, 'organization', '') or ''
 
    def get_max_marks(self, obj):
        try:
            from app_eval.models import PassingRequirement
            requirement = PassingRequirement.objects.filter(status='Active').first()
            return requirement.presentation_max_marks if requirement else 50
        except:
            return 50
       
 
 
class PersonalInterviewSerializer(serializers.ModelSerializer):
    """Enhanced serializer for personal interview listing with presentation data"""
   
    # Basic proposal fields
    id = serializers.CharField(source='proposal_id')
    call = serializers.CharField(source='service.name')
    orgType = serializers.CharField(source='org_type')
    orgName = serializers.SerializerMethodField()
    subject = serializers.CharField()
    description = serializers.CharField()
    status = serializers.SerializerMethodField()
    grantFromTTDF = serializers.SerializerMethodField()
    fundsGranted = serializers.SerializerMethodField()  
    contributionByApplicant = serializers.SerializerMethodField()
    shortlist = serializers.SerializerMethodField()
    submissionDate = serializers.DateTimeField(source='created_at')
    contactPerson = serializers.SerializerMethodField()
    contactEmail = serializers.SerializerMethodField()
    funds_requested = serializers.SerializerMethodField()
   
    # Document links
    committeeDetails = serializers.SerializerMethodField()
    applicationDocument = serializers.SerializerMethodField()
    administrativeScreeningDocument = serializers.SerializerMethodField()
    technicalScreeningDocument = serializers.SerializerMethodField()
    technicalEvaluationDocument = serializers.SerializerMethodField()
   
    # Enhanced presentation and evaluation data for multiple evaluators
    presentation = serializers.SerializerMethodField()
    evaluation_data = serializers.SerializerMethodField()
   
    # New fields for multiple evaluators
    all_evaluators = serializers.SerializerMethodField()
    average_marks = serializers.SerializerMethodField()
    total_evaluators = serializers.SerializerMethodField()
 
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'call', 'orgType', 'orgName', 'subject', 'description', 'status',
            'grantFromTTDF','funds_requested', 'fundsGranted', 'shortlist', 'contributionByApplicant',
            'submissionDate', 'contactPerson', 'contactEmail', 'committeeDetails',
            'applicationDocument', 'administrativeScreeningDocument',
            'technicalScreeningDocument', 'technicalEvaluationDocument',
            'presentation', 'evaluation_data', 'all_evaluators', 'average_marks', 'total_evaluators'
        ]
   
    def get_status(self, obj):
        """Determine status based on presentation completion across all evaluators"""
        presentations = obj.presentations.all()
        if not presentations:
            return 'pending'
       
        # Check if all materials are assigned
        materials_complete = any(
            p.document_uploaded for p in presentations
        )
       
        # Check if all evaluators have completed evaluation
        all_evaluated = all(
            p.is_evaluation_completed for p in presentations if p.evaluator
        )
       
        # Check if admin has made final decision
        final_decision_made = any(
            p.final_decision in ['shortlisted', 'rejected'] for p in presentations
        )
       
        if final_decision_made:
            return 'evaluated'
        elif all_evaluated and materials_complete:
            return 'assigned'  # Ready for admin decision
        elif materials_complete:
            return 'assigned'  # Materials ready, waiting for evaluation
        else:
            return 'pending'
   
    def get_orgName(self, obj):
        return getattr(obj.applicant, 'organization', '') or ''
 
    def get_contactPerson(self, obj):
        user = getattr(obj, 'applicant', None)
        if user:
            return getattr(user, 'full_name', '') or getattr(user, 'get_full_name', lambda: '')() or user.email
        return ''
 
    def get_contactEmail(self, obj):
        return obj.contact_email or ''
   
    def get_grantFromTTDF(self, obj):
        latest = obj.milestones.order_by('-created_at').first()
        return latest.grant_from_ttdf if latest else None
 
    def get_funds_requested(self, obj):
        latest = obj.milestones.order_by('-created_at').first()
        return latest.funds_requested if latest else None
 
    def get_fundsGranted(self, obj):
        latest = obj.milestones.order_by('-created_at').first()
        return latest.initial_grant_from_ttdf if latest else None
             
    def get_contributionByApplicant(self, obj):
        latest = obj.milestones.order_by('-created_at').first()
        return latest.revised_contri_applicant if latest else None
 
    def get_shortlist(self, obj):
        """Check if any presentation is shortlisted"""
        presentations = obj.presentations.all()
        return any(p.final_decision == 'shortlisted' for p in presentations)
 
    def get_committeeDetails(self, obj):
        committee = (
            ScreeningCommittee.objects
            .filter(service=obj.service, committee_type='administrative')
            .first()
        )
        if not committee:
            return None
 
        members = [m.user.full_name for m in committee.members.all()]
        return {
            'name': committee.name,
            'head': committee.head.full_name if committee.head else None,
            'members': members,
            'documentUploaded': ScreeningRecord.objects.filter(proposal=obj).exists(),
            'evaluationStopped': not committee.is_active,
        }
 
    def get_applicationDocument(self, obj):
        field = getattr(obj, 'applicationDocument', None)
        return field.url if field else None
 
    def get_administrativeScreeningDocument(self, obj):
        rec = obj.screening_records.order_by('-cycle').first()
        return rec.evaluated_document.url if rec and rec.evaluated_document else None
 
    def get_technicalScreeningDocument(self, obj):
        admin_rec = obj.screening_records.order_by('-cycle').first()
        tech = getattr(admin_rec, 'technical_record', None)
        return tech.technical_document.url if tech and tech.technical_document else None
   
    def get_technicalEvaluationDocument(self, obj):
        try:
            tech_eval = TechnicalEvaluationRound.objects.filter(
                proposal__proposal_id=obj.proposal_id
            ).order_by('-evaluated_at').first()
            return tech_eval.technical_document.url if tech_eval and tech_eval.technical_document else None
        except Exception:
            return None
 
    def get_all_evaluators(self, obj):
        """Get all evaluators assigned to this proposal"""
        presentations = obj.presentations.all()
        evaluators = []
       
        for presentation in presentations:
            if presentation.evaluator:
                evaluators.append({
                    'id': presentation.evaluator.id,
                    'name': presentation.evaluator.get_full_name(),
                    'email': presentation.evaluator.email,
                    'marks': float(presentation.evaluator_marks) if presentation.evaluator_marks else None,
                    'remarks': presentation.evaluator_remarks,
                    'evaluated_at': presentation.evaluated_at,
                    'presentation_id': presentation.id
                })
       
        return evaluators
 
    def get_average_marks(self, obj):
        """Calculate average marks across all evaluators"""
        presentations = obj.presentations.filter(
            evaluator_marks__isnull=False
        )
       
        if not presentations:
            return 0
       
        total_marks = sum(float(p.evaluator_marks) for p in presentations)
        return round(total_marks / len(presentations), 2)
 
    def get_total_evaluators(self, obj):
        """Get total number of evaluators assigned"""
        return obj.presentations.filter(evaluator__isnull=False).count()
       
    def get_presentation(self, obj):
        """Enhanced presentation data combining all evaluators"""
        presentations = obj.presentations.all().order_by('-created_at')
       
        if not presentations:
            return None
 
        # Get the most recent presentation for basic info (video, document, etc.)
        main_presentation = presentations.first()
       
        # Get max marks for context
        try:
            from app_eval.models import PassingRequirement
            requirement = PassingRequirement.objects.filter(status='Active').first()
            max_marks = requirement.presentation_max_marks if requirement else 50
        except:
            max_marks = 50
 
        # Collect all evaluator data
        evaluators_data = []
        total_marks = 0
        evaluated_count = 0
       
        for presentation in presentations:
            if presentation.evaluator:
                evaluator_info = {
                    "id": presentation.id,
                    "evaluator_id": presentation.evaluator.id,
                    "evaluator_name": presentation.evaluator.get_full_name(),
                    "evaluator_email": presentation.evaluator.email,
                    "marks": float(presentation.evaluator_marks) if presentation.evaluator_marks else None,
                    "remarks": presentation.evaluator_remarks,
                    "evaluated_at": presentation.evaluated_at,
                    "is_completed": presentation.is_evaluation_completed
                }
                evaluators_data.append(evaluator_info)
               
                if presentation.evaluator_marks:
                    total_marks += float(presentation.evaluator_marks)
                    evaluated_count += 1
 
        # Calculate average marks
        average_marks = round(total_marks / evaluated_count, 2) if evaluated_count > 0 else 0
 
        # Determine overall status
        all_evaluated = all(e["is_completed"] for e in evaluators_data) and len(evaluators_data) > 0
        any_final_decision = any(p.final_decision in ['shortlisted', 'rejected'] for p in presentations)
 
        presentation_data = {
            "id": main_presentation.id,
            "video": main_presentation.video.url if main_presentation.video else None,
            "video_link": main_presentation.video_link,
            "document": main_presentation.document.url if main_presentation.document else None,
            "presentation_date": main_presentation.presentation_date,
            "document_uploaded": main_presentation.document_uploaded,
            "created_at": main_presentation.created_at,
            "updated_at": main_presentation.updated_at,
           
            # Combined evaluator information
            "evaluators": evaluators_data,
            "total_evaluators": len(evaluators_data),
            "evaluated_count": evaluated_count,
            "average_marks": average_marks,
            "total_marks": total_marks,
            "max_marks": max_marks,
           
            # Admin information (from most recent)
            "final_decision": main_presentation.final_decision,
            "admin_remarks": main_presentation.admin_remarks,
            "admin": main_presentation.admin.get_full_name() if main_presentation.admin else None,
            "admin_evaluated_at": main_presentation.admin_evaluated_at,
           
            # Combined status flags
            "is_ready_for_evaluation": main_presentation.is_ready_for_evaluation,
            "is_evaluation_completed": all_evaluated,
            "can_make_final_decision": all_evaluated and not any_final_decision,
           
            # Legacy fields for backward compatibility (using average/first evaluator)
            "evaluator": evaluators_data[0]["evaluator_name"] if evaluators_data else None,
            "evaluator_email": evaluators_data[0]["evaluator_email"] if evaluators_data else None,
            "evaluator_marks": average_marks,
            "evaluator_remarks": "; ".join([e["remarks"] for e in evaluators_data if e["remarks"]]),
            "evaluated_at": max([e["evaluated_at"] for e in evaluators_data if e["evaluated_at"]], default=None),
        }
 
        return presentation_data
 
    def get_evaluation_data(self, obj):
        """Technical evaluation data from app_eval - unchanged"""
        data = []
       
        assignments = obj.eval_assignments.select_related('evaluator').prefetch_related(
            'criteria_evaluations__criteria',
            'question_evaluations__question'
        )
 
        for assignment in assignments:
            criteria_evals = [
                {
                    'criteria': ce.criteria.name,
                    'total_marks': ce.criteria.total_marks,
                    'weightage': ce.criteria.weightage,
                    'marks_given': ce.marks_given,
                    'comments': ce.comments,
                    'date_evaluated': ce.date_evaluated,
                }
                for ce in assignment.criteria_evaluations.all()
            ]
 
            question_evals = [
                {
                    'question': qe.question.name,
                    'total_marks': qe.question.total_marks,
                    'weightage': qe.question.weightage,
                    'marks_given': qe.marks_given,
                    'comments': qe.comments,
                    'date_evaluated': qe.date_evaluated,
                }
                for qe in assignment.question_evaluations.all()
            ]
 
            data.append({
                'evaluator': assignment.evaluator.get_full_name() if assignment.evaluator else assignment.evaluator.email,
                'evaluated_at': assignment.evaluated_at,
                'criteria_evaluations': criteria_evals,
                'question_evaluations': question_evals,
                'current_trl': assignment.current_trl,
                'expected_trl': assignment.expected_trl,
                'remarks': assignment.remarks,
                'conflict_of_interest': assignment.conflict_of_interest,
                'conflict_remarks': assignment.conflict_remarks,
            })
 
        return data
  
   
# class UltraFastPresentationSerializer(serializers.ModelSerializer):
#     """Reads ONLY from cached fields for max speed."""
#     admin_name = serializers.CharField(source='cached_admin_name', default=None)
#     final_decision_display = serializers.CharField(source='cached_final_decision_display', default=None)
#     video_url = serializers.CharField(source='cached_video_url', default=None)
#     document_url = serializers.CharField(source='cached_document_url', default=None)
#     is_ready_for_evaluation = serializers.BooleanField(source='cached_is_ready_for_evaluation')
#     is_evaluation_completed = serializers.BooleanField(source='cached_is_evaluation_completed')
#     can_make_final_decision = serializers.BooleanField(source='cached_can_make_final_decision')
#     evaluator_name = serializers.CharField(source='cached_evaluator_name', default=None)
#     marks_summary = serializers.JSONField(source='cached_marks_summary', default=None)
#     applicant_data = serializers.JSONField(source='cached_applicant_data', default=None)
#     status = serializers.CharField(source='cached_status', default=None)

#     class Meta:
#         model = Presentation
#         fields = [
#             "id", "proposal_id",
#             "status",
#             "evaluator_name", "marks_summary", "applicant_data",
#             "video_url", "document_url", "video_link", "presentation_date",
#             "document_uploaded", "created_at", "updated_at",
#             "final_decision", "final_decision_display",
#             "admin_name", "admin_remarks", "admin_evaluated_at",
#             "is_ready_for_evaluation", "is_evaluation_completed", "can_make_final_decision"
#         ]


class UltraFastPresentationSerializer(serializers.ModelSerializer):
    admin_name = serializers.CharField(source='cached_admin_name', default=None)
    final_decision_display = serializers.CharField(source='cached_final_decision_display', default=None)
    video_url = serializers.CharField(source='cached_video_url', default=None)
    document_url = serializers.CharField(source='cached_document_url', default=None)
    is_ready_for_evaluation = serializers.BooleanField(source='cached_is_ready_for_evaluation')
    is_evaluation_completed = serializers.BooleanField(source='cached_is_evaluation_completed')
    can_make_final_decision = serializers.BooleanField(source='cached_can_make_final_decision')
    evaluator_name = serializers.CharField(source='cached_evaluator_name', default=None)
    marks_summary = serializers.JSONField(source='cached_marks_summary', default=None)
    applicant_data = serializers.JSONField(source='cached_applicant_data', default=None)
    status = serializers.CharField(source='cached_status', default=None)

    class Meta:
        model = Presentation
        fields = [
            "id", "proposal_id",
            "status",
            "evaluator_name", "marks_summary", "applicant_data",
            "video_url", "document_url", "video_link", "presentation_date",
            "document_uploaded", "created_at", "updated_at",
            "final_decision", "final_decision_display",
            "admin_name", "admin_remarks", "admin_evaluated_at",
            "is_ready_for_evaluation", "is_evaluation_completed", "can_make_final_decision"
        ]


class UltraFastFormSubmissionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='proposal_id')
    call = serializers.CharField(source='service.name')
    orgType = serializers.CharField(source='org_type')
    orgName = serializers.SerializerMethodField()
    subject = serializers.CharField()
    description = serializers.CharField()
    status = serializers.SerializerMethodField()
    submissionDate = serializers.DateTimeField(source='created_at')
    contactPerson = serializers.SerializerMethodField()
    contactEmail = serializers.SerializerMethodField()
    average_marks = serializers.SerializerMethodField()
    total_evaluators = serializers.SerializerMethodField()
    presentation = serializers.SerializerMethodField()

    class Meta:
        model = FormSubmission
        fields = [
            'id', 'call', 'orgType', 'orgName', 'subject', 'description',
            'status', 'submissionDate', 'contactPerson', 'contactEmail',
            'average_marks', 'total_evaluators', 'presentation'
        ]

    def get_orgName(self, obj):
        # Use prefetched applicant
        return getattr(obj.applicant, 'organization', '')

    def get_contactPerson(self, obj):
        user = getattr(obj, 'applicant', None)
        if not user:
            return ''
        return getattr(user, 'full_name', '') or (user.get_full_name() if hasattr(user, "get_full_name") else user.email)

    def get_contactEmail(self, obj):
        return getattr(obj, "contact_email", "")

    def get_status(self, obj):
        presentations = list(obj.presentations.all())
        if presentations and hasattr(presentations, 'all'):
            presentations = list(presentations.all())
        if not presentations:
            return 'pending'
        return presentations[0].cached_status or 'pending'

    def get_average_marks(self, obj):
        presentations = list(obj.presentations.all())
        if hasattr(presentations, 'all'):
            presentations = list(presentations.all())
        scored = [p for p in presentations if p.cached_marks_summary and p.cached_marks_summary.get('marks') is not None]
        if not scored:
            return 0
        total_marks = sum(float(p.cached_marks_summary.get('marks')) for p in scored)
        return round(total_marks / len(scored), 2)

    def get_total_evaluators(self, obj):
        presentations = list(obj.presentations.all())
        if hasattr(presentations, 'all'):
            presentations = list(presentations.all())
        return sum(1 for p in presentations if getattr(p, 'evaluator', None) is not None)

    def get_presentation(self, obj):
        presentations = list(obj.presentations.all())
        if hasattr(presentations, 'all'):
            presentations = list(presentations.all())
        if not presentations:
            return None
        main_presentation = presentations[0]
        cached = main_presentation.cached_marks_summary or {}
        evaluators_data = []
        total_marks = 0
        evaluated_count = 0
        for p in presentations:
            if getattr(p, 'evaluator', None):
                marks = (p.cached_marks_summary or {}).get('marks')
                remarks = (p.cached_marks_summary or {}).get('remarks')
                evaluated_at = (p.cached_marks_summary or {}).get('evaluated_at')
                is_completed = getattr(p, 'is_evaluation_completed', False)
                evaluators_data.append({
                    "id": p.id,
                    "evaluator_id": p.evaluator.id if p.evaluator else None,
                    "evaluator_name": p.cached_evaluator_name,
                    "evaluator_email": (p.cached_applicant_data or {}).get('email'),
                    "marks": marks,
                    "remarks": remarks,
                    "evaluated_at": evaluated_at,
                    "is_completed": is_completed
                })
                if marks is not None:
                    total_marks += float(marks)
                    evaluated_count += 1
        average_marks = round(total_marks / evaluated_count, 2) if evaluated_count > 0 else 0

        return {
            "id": main_presentation.id,
            "video": main_presentation.video.url if main_presentation.video else None,
            "video_link": main_presentation.video_link,
            "document": main_presentation.document.url if main_presentation.document else None,
            "presentation_date": main_presentation.presentation_date,
            "document_uploaded": main_presentation.document_uploaded,
            "created_at": main_presentation.created_at,
            "updated_at": main_presentation.updated_at,
            "evaluators": evaluators_data,
            "total_evaluators": len(evaluators_data),
            "evaluated_count": evaluated_count,
            "average_marks": average_marks,
            "final_decision": main_presentation.final_decision,
            "admin_remarks": main_presentation.admin_remarks,
            "admin": main_presentation.admin.get_full_name() if main_presentation.admin else None,
            "admin_evaluated_at": main_presentation.admin_evaluated_at,
            "is_ready_for_evaluation": getattr(main_presentation, 'is_ready_for_evaluation', False),
            "is_evaluation_completed": getattr(main_presentation, 'is_evaluation_completed', False),
            "can_make_final_decision": getattr(main_presentation, 'can_make_final_decision', False),
            "evaluator": evaluators_data[0]["evaluator_name"] if evaluators_data else None,
            "evaluator_email": evaluators_data[0]["evaluator_email"] if evaluators_data else None,
            "evaluator_marks": average_marks,
            "evaluator_remarks": "; ".join([e["remarks"] for e in evaluators_data if e["remarks"]]),
            "evaluated_at": max([e["evaluated_at"] for e in evaluators_data if e["evaluated_at"]], default=None),
        }
    

# def get_presentation(self, obj):
    #     t1 = time.perf_counter()
    #     presentations = list(obj.presentations.all())
    #     if hasattr(presentations, 'all'):
    #         presentations = list(presentations.all())
    #     if not presentations:
    #         presentation_data = None
    #     else:
    #         main_presentation = presentations[0]
    #         cached = main_presentation.cached_marks_summary or {}
    #         evaluators_data = []
    #         total_marks = 0
    #         evaluated_count = 0
    #         for p in presentations:
    #             if getattr(p, 'evaluator', None):
    #                 marks = (p.cached_marks_summary or {}).get('marks')
    #                 remarks = (p.cached_marks_summary or {}).get('remarks')
    #                 evaluated_at = (p.cached_marks_summary or {}).get('evaluated_at')
    #                 is_completed = getattr(p, 'is_evaluation_completed', False)
    #                 evaluators_data.append({
    #                     "id": p.id,
    #                     "evaluator_id": p.evaluator.id if p.evaluator else None,
    #                     "evaluator_name": p.cached_evaluator_name,
    #                     "evaluator_email": (p.cached_applicant_data or {}).get('email'),
    #                     "marks": marks,
    #                     "remarks": remarks,
    #                     "evaluated_at": evaluated_at,
    #                     "is_completed": is_completed
    #                 })
    #                 if marks is not None:
    #                     total_marks += float(marks)
    #                     evaluated_count += 1
    #         average_marks = round(total_marks / evaluated_count, 2) if evaluated_count > 0 else 0

    #         presentation_data = {
    #             "id": main_presentation.id,
    #             "video": main_presentation.video.url if main_presentation.video else None,
    #             "video_link": main_presentation.video_link,
    #             "document": main_presentation.document.url if main_presentation.document else None,
    #             "presentation_date": main_presentation.presentation_date,
    #             "document_uploaded": main_presentation.document_uploaded,
    #             "created_at": main_presentation.created_at,
    #             "updated_at": main_presentation.updated_at,
    #             "evaluators": evaluators_data,
    #             "total_evaluators": len(evaluators_data),
    #             "evaluated_count": evaluated_count,
    #             "average_marks": average_marks,
    #             "final_decision": main_presentation.final_decision,
    #             "admin_remarks": main_presentation.admin_remarks,
    #             "admin": main_presentation.admin.get_full_name() if main_presentation.admin else None,
    #             "admin_evaluated_at": main_presentation.admin_evaluated_at,
    #             "is_ready_for_evaluation": getattr(main_presentation, 'is_ready_for_evaluation', False),
    #             "is_evaluation_completed": getattr(main_presentation, 'is_evaluation_completed', False),
    #             "can_make_final_decision": getattr(main_presentation, 'can_make_final_decision', False),
    #             "evaluator": evaluators_data[0]["evaluator_name"] if evaluators_data else None,
    #             "evaluator_email": evaluators_data[0]["evaluator_email"] if evaluators_data else None,
    #             "evaluator_marks": average_marks,
    #             "evaluator_remarks": "; ".join([e["remarks"] for e in evaluators_data if e["remarks"]]),
    #             "evaluated_at": max([e["evaluated_at"] for e in evaluators_data if e["evaluated_at"]], default=None),
    #         }
    #     t2 = time.perf_counter()
    #     print(f"UltraFast get_presentation({obj.proposal_id}) took {t2-t1:.3f}s")
    #     return presentation_data






#     id = serializers.CharField(source='proposal_id')
#     call = serializers.CharField(source='service.name')
#     orgType = serializers.CharField(source='org_type')
#     orgName = serializers.SerializerMethodField()
#     subject = serializers.CharField()
#     description = serializers.CharField()
#     status = serializers.SerializerMethodField()
#     grantFromTTDF = serializers.SerializerMethodField()
#     fundsGranted = serializers.SerializerMethodField()
#     contributionByApplicant = serializers.SerializerMethodField()
#     shortlist = serializers.SerializerMethodField()
#     submissionDate = serializers.DateTimeField(source='created_at')
#     contactPerson = serializers.SerializerMethodField()
#     contactEmail = serializers.SerializerMethodField()
#     funds_requested = serializers.SerializerMethodField()
#     committeeDetails = serializers.SerializerMethodField()
#     applicationDocument = serializers.SerializerMethodField()
#     administrativeScreeningDocument = serializers.SerializerMethodField()
#     technicalScreeningDocument = serializers.SerializerMethodField()
#     technicalEvaluationDocument = serializers.SerializerMethodField()
#     presentation = serializers.SerializerMethodField()
#     evaluation_data = serializers.SerializerMethodField()
#     all_evaluators = serializers.SerializerMethodField()
#     average_marks = serializers.SerializerMethodField()
#     total_evaluators = serializers.SerializerMethodField()

#     class Meta:
#         model = FormSubmission
#         fields = [
#             'id', 'call', 'orgType', 'orgName', 'subject', 'description', 'status',
#             'grantFromTTDF', 'funds_requested', 'fundsGranted', 'shortlist', 'contributionByApplicant',
#             'submissionDate', 'contactPerson', 'contactEmail', 'committeeDetails',
#             'applicationDocument', 'administrativeScreeningDocument',
#             'technicalScreeningDocument', 'technicalEvaluationDocument',
#             'presentation', 'evaluation_data', 'all_evaluators', 'average_marks', 'total_evaluators'
#         ]

#     def get_orgName(self, obj):
#         return getattr(obj.applicant, 'organization', '') or ''

#     def get_contactPerson(self, obj):
#         user = getattr(obj, 'applicant', None)
#         if user:
#             return getattr(user, 'full_name', '') or (user.get_full_name() if hasattr(user, "get_full_name") else '') or user.email
#         return ''

#     def get_contactEmail(self, obj):
#         return getattr(obj, "contact_email", "") or ""

#     def get_status(self, obj):
#         presentations = list(obj.presentations.order_by('-created_at'))
#         if not presentations:
#             return 'pending'
#         return presentations[0].cached_status or 'pending'

#     def get_grantFromTTDF(self, obj):
#         milestones = list(obj.milestones.order_by('-created_at'))
#         latest = milestones[0] if milestones else None
#         return latest.grant_from_ttdf if latest else None

#     def get_funds_requested(self, obj):
#         milestones = list(obj.milestones.order_by('-created_at'))
#         latest = milestones[0] if milestones else None
#         return latest.funds_requested if latest else None

#     def get_fundsGranted(self, obj):
#         milestones = list(obj.milestones.order_by('-created_at'))
#         latest = milestones[0] if milestones else None
#         return latest.initial_grant_from_ttdf if latest else None

#     def get_contributionByApplicant(self, obj):
#         milestones = list(obj.milestones.order_by('-created_at'))
#         latest = milestones[0] if milestones else None
#         return latest.revised_contri_applicant if latest else None

#     def get_shortlist(self, obj):
#         presentations = list(obj.presentations.order_by('-created_at'))
#         return any(p.final_decision == 'shortlisted' for p in presentations)

#     def get_committeeDetails(self, obj):
#         # WARNING: Slightly slower; if possible, prefetch committee and .members
#         from screening.models import ScreeningCommittee, ScreeningRecord
#         committee = (
#             ScreeningCommittee.objects
#             .filter(service=obj.service, committee_type='administrative')
#             .first()
#         )
#         if not committee:
#             return None
#         members = [m.user.full_name for m in committee.members.all()]
#         return {
#             'name': committee.name,
#             'head': committee.head.full_name if committee.head else None,
#             'members': members,
#             'documentUploaded': ScreeningRecord.objects.filter(proposal=obj).exists(),
#             'evaluationStopped': not committee.is_active,
#         }

#     def get_applicationDocument(self, obj):
#         field = getattr(obj, 'applicationDocument', None)
#         return field.url if field else None

#     def get_administrativeScreeningDocument(self, obj):
#         screening_records = list(obj.screening_records.order_by('-cycle'))
#         rec = screening_records[0] if screening_records else None
#         return rec.evaluated_document.url if rec and rec.evaluated_document else None

#     def get_technicalScreeningDocument(self, obj):
#         screening_records = list(obj.screening_records.order_by('-cycle'))
#         admin_rec = screening_records[0] if screening_records else None
#         tech = getattr(admin_rec, 'technical_record', None)
#         return tech.technical_document.url if tech and tech.technical_document else None

#     def get_technicalEvaluationDocument(self, obj):
#         from app_eval.models import TechnicalEvaluationRound
#         tech_eval = (
#             TechnicalEvaluationRound.objects
#             .filter(proposal__proposal_id=obj.proposal_id)
#             .order_by('-evaluated_at')
#             .first()
#         )
#         return tech_eval.technical_document.url if tech_eval and tech_eval.technical_document else None

#     def get_all_evaluators(self, obj):
#         presentations = list(obj.presentations.order_by('-created_at'))
#         evaluators = []
#         for p in presentations:
#             if p.evaluator:
#                 evaluators.append({
#                     'id': p.id,
#                     'name': p.cached_evaluator_name,
#                     'email': (p.cached_applicant_data or {}).get('email'),
#                     'marks': (p.cached_marks_summary or {}).get('marks'),
#                     'remarks': (p.cached_marks_summary or {}).get('remarks'),
#                     'evaluated_at': (p.cached_marks_summary or {}).get('evaluated_at'),
#                     'presentation_id': p.id
#                 })
#         return evaluators

#     def get_average_marks(self, obj):
#         presentations = list(obj.presentations.order_by('-created_at'))
#         scored = [p for p in presentations if p.cached_marks_summary and p.cached_marks_summary.get('marks') is not None]
#         if not scored:
#             return 0
#         total_marks = sum(float(p.cached_marks_summary.get('marks')) for p in scored)
#         return round(total_marks / len(scored), 2)

#     def get_total_evaluators(self, obj):
#         presentations = list(obj.presentations.order_by('-created_at'))
#         return sum(1 for p in presentations if p.evaluator is not None)

#     def get_presentation(self, obj):
#         presentations = list(obj.presentations.order_by('-created_at'))
#         if not presentations:
#             return None
#         main_presentation = presentations[0]
#         cached = main_presentation.cached_marks_summary or {}

#         evaluators_data = []
#         total_marks = 0
#         evaluated_count = 0
#         for p in presentations:
#             if p.evaluator:
#                 marks = (p.cached_marks_summary or {}).get('marks')
#                 remarks = (p.cached_marks_summary or {}).get('remarks')
#                 evaluated_at = (p.cached_marks_summary or {}).get('evaluated_at')
#                 is_completed = p.is_evaluation_completed
#                 evaluators_data.append({
#                     "id": p.id,
#                     "evaluator_id": p.evaluator.id,
#                     "evaluator_name": p.cached_evaluator_name,
#                     "evaluator_email": (p.cached_applicant_data or {}).get('email'),
#                     "marks": marks,
#                     "remarks": remarks,
#                     "evaluated_at": evaluated_at,
#                     "is_completed": is_completed
#                 })
#                 if marks is not None:
#                     total_marks += float(marks)
#                     evaluated_count += 1

#         average_marks = round(total_marks / evaluated_count, 2) if evaluated_count > 0 else 0
#         all_evaluated = all(e["is_completed"] for e in evaluators_data) and len(evaluators_data) > 0
#         any_final_decision = any(p.final_decision in ['shortlisted', 'rejected'] for p in presentations)

#         # Max marks (static or from model if you prefer)
#         try:
#             from app_eval.models import PassingRequirement
#             requirement = PassingRequirement.objects.filter(status='Active').first()
#             max_marks = requirement.presentation_max_marks if requirement else 50
#         except:
#             max_marks = 50

#         return {
#             "id": main_presentation.id,
#             "video": main_presentation.video.url if main_presentation.video else None,
#             "video_link": main_presentation.video_link,
#             "document": main_presentation.document.url if main_presentation.document else None,
#             "presentation_date": main_presentation.presentation_date,
#             "document_uploaded": main_presentation.document_uploaded,
#             "created_at": main_presentation.created_at,
#             "updated_at": main_presentation.updated_at,
#             "evaluators": evaluators_data,
#             "total_evaluators": len(evaluators_data),
#             "evaluated_count": evaluated_count,
#             "average_marks": average_marks,
#             "total_marks": total_marks,
#             "max_marks": max_marks,
#             "final_decision": main_presentation.final_decision,
#             "admin_remarks": main_presentation.admin_remarks,
#             "admin": main_presentation.admin.get_full_name() if main_presentation.admin else None,
#             "admin_evaluated_at": main_presentation.admin_evaluated_at,
#             "is_ready_for_evaluation": main_presentation.is_ready_for_evaluation,
#             "is_evaluation_completed": all_evaluated,
#             "can_make_final_decision": all_evaluated and not any_final_decision,
#             "evaluator": evaluators_data[0]["evaluator_name"] if evaluators_data else None,
#             "evaluator_email": evaluators_data[0]["evaluator_email"] if evaluators_data else None,
#             "evaluator_marks": average_marks,
#             "evaluator_remarks": "; ".join([e["remarks"] for e in evaluators_data if e["remarks"]]),
#             "evaluated_at": max([e["evaluated_at"] for e in evaluators_data if e["evaluated_at"]], default=None),
#         }

#     def get_evaluation_data(self, obj):
#         # Restored from old code! (you MUST prefetch these, or this will be slow)
#         data = []
#         assignments = obj.eval_assignments.select_related('evaluator').prefetch_related(
#             'criteria_evaluations__criteria',
#             'question_evaluations__question'
#         )
#         for assignment in assignments:
#             criteria_evals = [
#                 {
#                     'criteria': ce.criteria.name,
#                     'total_marks': ce.criteria.total_marks,
#                     'weightage': ce.criteria.weightage,
#                     'marks_given': ce.marks_given,
#                     'comments': ce.comments,
#                     'date_evaluated': ce.date_evaluated,
#                 }
#                 for ce in assignment.criteria_evaluations.all()
#             ]
#             question_evals = [
#                 {
#                     'question': qe.question.name,
#                     'total_marks': qe.question.total_marks,
#                     'weightage': qe.question.weightage,
#                     'marks_given': qe.marks_given,
#                     'comments': qe.comments,
#                     'date_evaluated': qe.date_evaluated,
#                 }
#                 for qe in assignment.question_evaluations.all()
#             ]
#             data.append({
#                 'evaluator': assignment.evaluator.get_full_name() if assignment.evaluator else getattr(assignment.evaluator, "email", None),
#                 'evaluated_at': assignment.evaluated_at,
#                 'criteria_evaluations': criteria_evals,
#                 'question_evaluations': question_evals,
#                 'current_trl': assignment.current_trl,
#                 'expected_trl': assignment.expected_trl,
#                 'remarks': assignment.remarks,
#                 'conflict_of_interest': assignment.conflict_of_interest,
#                 'conflict_remarks': assignment.conflict_remarks,
#             })
#         return data

