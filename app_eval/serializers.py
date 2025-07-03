# app_eval/serializers.py
from rest_framework import serializers
from dynamic_form.models import FormSubmission
from screening.models import ScreeningRecord, TechnicalScreeningRecord
from django.contrib.auth import get_user_model
from .models import (
    EvaluationItem, CriteriaType, Evaluator, 
    EvaluationAssignment, CriteriaEvaluation, QuestionEvaluation, EvaluationCutoff,PassingRequirement
)
from decimal import Decimal
from configuration.models import ScreeningCommittee

User = get_user_model()


class EvaluatorEmailSerializer(serializers.ModelSerializer):
    # Rename `email` → `user` in the output
    user = serializers.EmailField(source='email')

    class Meta:
        model  = User
        fields = ['id','user']


class EvaluatorEmailField(serializers.RelatedField):
    def to_representation(self, value):
        # how it appears in responses
        return value.user.email

    def to_internal_value(self, data):
        # how input “data” is converted into an Evaluator instance
        try:
            user = User.objects.get(email=data)
        except User.DoesNotExist:
            raise serializers.ValidationError(f"No user with email {data}")

        try:
            return Evaluator.objects.get(user=user)
        except Evaluator.DoesNotExist:
            raise serializers.ValidationError(f"No evaluator for user {data}")

class AssignmentCreateSerializer(serializers.ModelSerializer):
    form_submission = serializers.SlugRelatedField(
        slug_field='proposal_id',
        queryset=FormSubmission.objects.all()
    )
    evaluator = serializers.PrimaryKeyRelatedField(
        # only allow Users who have the “Evaluator” role
        queryset=User.objects.filter(roles__name='Evaluator')
    )

    class Meta:
        model  = EvaluationAssignment
        fields = ['form_submission', 'evaluator']


class EvaluationSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationAssignment
        fields = [
            'expected_trl', 'remarks', 'conflict_of_interest', 'conflict_remarks',
            'total_marks_assigned', 'is_completed'
        ]

class EvaluationAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationAssignment
        fields = '__all__'
        read_only_fields = ['current_trl', 'date_assigned', 'evaluated_at']


class PassingRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PassingRequirement
        fields = '__all__'

    def validate(self, attrs):
        requirement_name = attrs.get('requirement_name', None)

        if requirement_name:
            qs = PassingRequirement.objects.filter(requirement_name__iexact=requirement_name)

            # If updating, exclude the current instance
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    'requirement_name': "Requirement name already exists."
                })

        return attrs


class EvaluationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationItem
        fields = '__all__'

class GeneralPoolItemSerializer(serializers.ModelSerializer):
    allocated = serializers.DecimalField(source='total_marks', max_digits=5, decimal_places=2)
    type = serializers.CharField()

    class Meta:
        model = EvaluationItem
        fields = [
            'id', 'name', 'allocated', 'weightage',
            'memberType', 'status', 'description', 'key', 'type'
        ]

class CriteriaTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriteriaType
        fields = '__all__'

class EvaluatorSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Evaluator
        fields = '__all__'


class CriteriaEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriteriaEvaluation
        fields = '__all__'

class QuestionEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionEvaluation
        fields = '__all__'

class EvaluationCutoffSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationCutoff
        fields = '__all__'



class TechnicalEvaluationSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    submissionDate = serializers.SerializerMethodField()
    techMembers = serializers.SerializerMethodField()
    evaluations = serializers.SerializerMethodField()
    totalMarks = serializers.SerializerMethodField()
    evaluationCriteria = serializers.SerializerMethodField()
    
    # Placeholders / cross-model fields
    call = serializers.SerializerMethodField()
    orgType = serializers.SerializerMethodField()
    orgName = serializers.SerializerMethodField()
    fundsRequested = serializers.SerializerMethodField()
    document = serializers.SerializerMethodField()
    shortlist = serializers.SerializerMethodField()
    committee = serializers.SerializerMethodField()
    contactPerson = serializers.SerializerMethodField()
    contactEmail = serializers.SerializerMethodField()
    adminScreeningDoc = serializers.SerializerMethodField()
    techScreeningDoc = serializers.SerializerMethodField()
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'call', 'orgType', 'orgName', 'subject', 'description', 'status',
            'fundsRequested', 'document', 'shortlist', 'committee', 'submissionDate',
            'contactPerson', 'contactEmail', 'techMembers', 'evaluations', 'totalMarks',
            'adminScreeningDoc', 'techScreeningDoc', 'evaluationCriteria'
        ]
    
    def get_id(self, obj):
        return obj.proposal_id or f"FORM-{obj.form_id}"
    
    def get_subject(self, obj):
        for field in ('subject', 'title', 'name'):
            val = getattr(obj, field, None)
            if val:
                return val
        return f"Form {obj.form_id}"
    
    def get_description(self, obj):
        return obj.description or ""
    
    def get_status(self, obj):
        rec = obj.screening_records.filter(technical_evaluated=True).first()
        return "evaluated" if rec else "pending"
    
    def get_submissionDate(self, obj):
        dt = getattr(obj, 'date_created', None) or getattr(obj, 'submitted_at', None)
        if dt:
            return dt.strftime("%Y-%m-%d")
        rec = obj.screening_records.first()
        return rec.admin_screened_at.strftime("%Y-%m-%d") if rec else datetime.now().strftime("%Y-%m-%d")
    
    def get_techMembers(self, obj):
        # all assignments
        assignments = obj.eval_assignments.all()
        members = [a.evaluator.get_full_name() for a in assignments]
        
        # plus the one from technical_record
        rec = obj.screening_records.filter(technical_evaluated=True).first()
        if rec and hasattr(rec, 'technical_record'):
            te = rec.technical_record.technical_evaluator
            if te:
                name = te.get_full_name()
                if name not in members:
                    members.append(name)
        return members
    
    def get_evaluations(self, obj):
        result = []
        assignments = obj.eval_assignments.all()
        
        for a in assignments:
            name = a.evaluator.get_full_name()
            crits = CriteriaEvaluation.objects.filter(assignment=a)
            total = weighted = 0
            comments = []
            
            for ce in crits:
                w = ce.criteria.weightage / 100
                total += ce.marks_given * w
                weighted += ce.criteria.weightage
                if ce.comments:
                    comments.append(ce.comments)
            
            marks = round(min(total * 100 / weighted, 100), 1) if weighted else 0
            result.append({
                'member': name,
                'marks': marks,
                'comments': ' '.join(comments) if comments else "Excellent technical approach"
            })
        
        # add the technical_record evaluator if set
        rec = obj.screening_records.filter(technical_evaluated=True).first()
        if rec and hasattr(rec, 'technical_record'):
            tr = rec.technical_record
            if tr.technical_evaluator:
                nm = tr.technical_evaluator.get_full_name()
                if not any(r['member']==nm for r in result):
                    result.append({
                        'member': nm,
                        'marks': float(tr.technical_marks or 0),
                        'comments': tr.technical_remarks or "Excellent technical approach"
                    })
        return result
    
    def get_totalMarks(self, obj):
        evs = self.get_evaluations(obj)
        return round(sum(item['marks'] for item in evs) / len(evs), 1) if evs else 0
    
    def get_evaluationCriteria(self, obj):
        items = EvaluationItem.objects.filter(type='criteria')
        assignments = obj.eval_assignments.all()
        result = []
        
        for crit in items:
            member_evals = []
            
            for a in assignments:
                name = a.evaluator.get_full_name()
                try:
                    ce = CriteriaEvaluation.objects.get(assignment=a, criteria=crit)
                    m = ce.marks_given
                    c = ce.comments or "Well-architected solution"
                except CriteriaEvaluation.DoesNotExist:
                    m = crit.total_marks * Decimal('0.85')
                    c = "Well-architected solution"
                
                member_evals.append({
                    'member': name,
                    'marks': m,
                    'comments': c
                })
            
            result.append({
                'criteriaName': crit.name,
                'keyName': crit.key,
                'maxMarks': crit.total_marks,
                'weightage': f"{crit.weightage}%",
                'memberEvaluations': member_evals
            })
        
        return result
    
    # --- placeholder getters below ---
    def get_call(self, obj):            return "Call 1 - 2025"
    def get_orgType(self, obj):         return "EY India"
    def get_orgName(self, obj):         return "Audit Innovation"
    def get_fundsRequested(self, obj):  return "45,000"
    
    def get_document(self, obj):
        rec = obj.screening_records.first()
        if rec and rec.evaluated_document:
            return rec.evaluated_document.name.rsplit('/',1)[-1]
        return f"{self.get_id(obj).lower()}.pdf"
    
    def get_shortlist(self, obj):
        rec = obj.screening_records.first()
        if rec and hasattr(rec, 'technical_record') and rec.technical_record:
            return rec.technical_record.technical_decision == 'accepted'
        try:
            cut = EvaluationCutoff.objects.get(form_submission=obj)
            return self.get_totalMarks(obj) >= cut.cutoff_marks
        except EvaluationCutoff.DoesNotExist:
            return True
    
    def get_committee(self, obj):        return "AI Committee"
    def get_contactPerson(self, obj):
        rec = obj.screening_records.first()
        return rec.contact_name if rec and rec.contact_name else (obj.contact_name or "Priya Sharma")
    def get_contactEmail(self, obj):
        rec = obj.screening_records.first()
        return rec.contact_email if rec and rec.contact_email else (obj.contact_email or "priya.s@ey.com")
    def get_adminScreeningDoc(self, obj):
        rec = obj.screening_records.first()
        if rec and rec.evaluated_document:
            return rec.evaluated_document.name.rsplit('/',1)[-1]
        return f"admin_screening_{self.get_id(obj).lower()}.pdf"
    def get_techScreeningDoc(self, obj):
        rec = obj.screening_records.filter(technical_evaluated=True).first()
        tr = getattr(rec, 'technical_record', None)
        if tr and tr.technical_document:
            return tr.technical_document.name.rsplit('/',1)[-1]
        return f"tech_screening_{self.get_id(obj).lower()}.pdf"
  

class TechnicalEvaluationDashboardSerializer(serializers.ModelSerializer):
    id                          = serializers.CharField(source='proposal_id')
    call                        = serializers.CharField(source='service.name')
    orgType                     = serializers.CharField(source='org_type')
    orgName                     = serializers.SerializerMethodField()
    subject                     = serializers.CharField()
    description                 = serializers.CharField()
    status                      = serializers.SerializerMethodField()
    fundsRequested              = serializers.SerializerMethodField()
    fundsGranted                = serializers.SerializerMethodField()
    applicationDocument         = serializers.SerializerMethodField()
    shortlist                   = serializers.SerializerMethodField()
    submissionDate              = serializers.DateTimeField(source='created_at')
    contactPerson               = serializers.SerializerMethodField()
    contactEmail                = serializers.SerializerMethodField()
    committeeDetails            = serializers.SerializerMethodField()
    administrativeScreeningDocument = serializers.SerializerMethodField()
    technicalScreeningDocument     = serializers.SerializerMethodField()
    evaluationAssignments       = EvaluationAssignmentSerializer(
                                      many=True,
                                      source='eval_assignments'
                                  )

    class Meta:
        model  = FormSubmission
        fields = [
            'id', 'call', 'orgType', 'orgName', 'subject', 'description',
            'status', 'fundsRequested', 'fundsGranted', 'applicationDocument',
            'shortlist', 'submissionDate', 'contactPerson', 'contactEmail',
            'committeeDetails', 'administrativeScreeningDocument',
            'technicalScreeningDocument', 'evaluationAssignments'
        ]

    def get_orgName(self, obj):
        return getattr(obj.applicant, 'organization', '') or ''

    def get_status(self, obj):
        record = obj.screening_records.order_by('-cycle').first()
        return record.admin_decision if record else 'pending'

    def get_fundsRequested(self, obj):
        latest = obj.milestones.order_by('-created_at').first()
        return latest.funds_requested if latest else None

    def get_fundsGranted(self, obj):
        latest = obj.milestones.order_by('-created_at').first()
        return latest.grant_from_ttdf if latest else None

    def get_applicationDocument(self, obj):
        doc = getattr(obj, 'applicationDocument', None)
        return doc.url if doc else None

    def get_shortlist(self, obj):
        rec = obj.screening_records.order_by('cycle').first()
        return bool(rec and rec.admin_decision == 'shortlisted')

    def get_contactPerson(self, obj):
        return obj.contact_name or ''

    def get_contactEmail(self, obj):
        return obj.contact_email or ''

    def get_committeeDetails(self, obj):
        committee = ScreeningCommittee.objects.filter(
            service=obj.service,
            committee_type='administrative'
        ).first()
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

    def get_administrativeScreeningDocument(self, obj):
        rec = obj.screening_records.order_by('-cycle').first()
        return rec.evaluated_document.url if rec and rec.evaluated_document else None

    def get_technicalScreeningDocument(self, obj):
        admin_rec = obj.screening_records.order_by('-cycle').first()
        tech      = getattr(admin_rec, 'technical_record', None)
        return tech.technical_document.url if tech and tech.technical_document else None



# Api 

# app_eval/serializers.py

class CriteriaDetailSerializer(serializers.ModelSerializer):
    maxMarks = serializers.DecimalField(source='total_marks', max_digits=5, decimal_places=2)
    weight = serializers.DecimalField(source='weightage', max_digits=5, decimal_places=2)

    class Meta:
        model = EvaluationItem
        fields = ['id', 'name', 'description', 'maxMarks', 'weight']
