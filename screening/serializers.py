# screening/serializers.py
from rest_framework import serializers
from .models import ScreeningRecord, TechnicalScreeningRecord
from dynamic_form.models import FormSubmission
from configuration.models import ScreeningCommittee
from screening.models import ScreeningRecord
from tech_eval.models import TechnicalEvaluationRound


class ScreeningRecordSerializer(serializers.ModelSerializer):
    proposal = serializers.SlugRelatedField(
        read_only=True,
        slug_field='proposal_id'
    )

    class Meta:
        model = ScreeningRecord
        fields = '__all__'
        read_only_fields = ['admin_screened_at', 'cycle']

class TechnicalScreeningRecordSerializer(serializers.ModelSerializer):
    proposal_id = serializers.CharField(
        source='screening_record.proposal.proposal_id',
        read_only=True
    )

    class Meta:
        model = TechnicalScreeningRecord
        fields = '__all__'
        read_only_fields = ['technical_screened_at']

# EVALUATOR VIEW - Administrative Screening
# class AdministrativeScreeningSerializer(serializers.ModelSerializer):
#     id = serializers.CharField(source='proposal_id')
#     call = serializers.CharField(source='service.name')
#     orgType = serializers.CharField(source='org_type')
#     orgName = serializers.SerializerMethodField()
#     subject = serializers.CharField()
#     description = serializers.CharField()
#     status = serializers.SerializerMethodField()
#     fundsRequested = serializers.SerializerMethodField()
#     fundsGranted = serializers.SerializerMethodField() 
#     applicationDocument = serializers.SerializerMethodField()
#     shortlist = serializers.SerializerMethodField()
#     submissionDate = serializers.DateTimeField(source='created_at')
#     contactPerson = serializers.SerializerMethodField()
#     contactEmail = serializers.SerializerMethodField()
#     committeeDetails = serializers.SerializerMethodField()
#     technical_evaluated = serializers.SerializerMethodField()
#     administrativeScreeningDocument = serializers.SerializerMethodField()
#     admin_decision = serializers.SerializerMethodField()
#     current_stage = serializers.SerializerMethodField()

#     class Meta:
#         model = FormSubmission
#         fields = [
#             'id','call','orgType','orgName','subject','description','status',
#             'fundsRequested','fundsGranted','applicationDocument','shortlist',
#             'submissionDate','contactPerson','contactEmail','committeeDetails',
#             'technical_evaluated','administrativeScreeningDocument','admin_decision','current_stage'
#         ]
    
#     def get_status(self, obj):
#         admin_record = obj.screening_records.order_by('-cycle').first()
#         if admin_record:
#             return admin_record.admin_decision
#         return 'pending'

#     def get_orgName(self, obj):
#         return getattr(obj.applicant, 'organization', '') or ''

#     def get_contactPerson(self, obj):
#         user = getattr(obj, 'applicant', None)
#         if user:
#             return getattr(user, 'full_name', '') or getattr(user, 'get_full_name', lambda: '')() or user.email
#         return ''

#     def get_contactEmail(self, obj):
#         return obj.contact_email or ''

#     def get_fundsRequested(self, obj):
#         m = obj.milestones.order_by('-created_at').first()
#         return m.funds_requested if m else None

#     def get_fundsGranted(self, obj):
#         m = obj.milestones.order_by('-created_at').first()
#         return m.grant_from_ttdf if m else None

#     def get_applicationDocument(self, obj):
#         return obj.applicationDocument.url if hasattr(obj, 'applicationDocument') and obj.applicationDocument else None

#     def get_shortlist(self, obj):
#         admin_record = obj.screening_records.order_by('-cycle').first()
#         return admin_record.admin_decision == 'shortlisted' if admin_record else False
    
#     def get_technical_evaluated(self, obj):
#         # TRUE if document uploaded (moves to evaluated tab automatically)
#         admin_record = obj.screening_records.order_by('-cycle').first()
#         return bool(admin_record and admin_record.evaluated_document)

#     def get_admin_decision(self, obj):
#         admin_record = obj.screening_records.order_by('-cycle').first()
#         return admin_record.admin_decision if admin_record else None

#     def get_current_stage(self, obj):
#         admin_record = obj.screening_records.order_by('-cycle').first()
        
#         if not admin_record:
#             return 'not_started'
        
#         if not admin_record.evaluated_document:
#             return 'awaiting_document'
            
#         if not admin_record.admin_evaluated:
#             return 'awaiting_admin_decision'
            
#         if admin_record.admin_decision == 'shortlisted':
#             technical_record = getattr(admin_record, 'technical_record', None)
#             if technical_record:
#                 if not technical_record.technical_document:
#                     return 'awaiting_technical_document'
#                 elif not technical_record.technical_evaluated:
#                     return 'awaiting_technical_decision'
#                 else:
#                     return 'technical_completed'
#             else:
#                 return 'admin_shortlisted'
#         else:
#             return 'admin_rejected'

#     def get_committeeDetails(self, obj):
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
#             'documentUploaded': bool(obj.screening_records.filter(evaluated_document__isnull=False).exists()),
#             'evaluationStopped': not committee.is_active,
#         }

#     def get_administrativeScreeningDocument(self, obj):
#         admin_record = obj.screening_records.order_by('-cycle').first()
#         return admin_record.evaluated_document.url if admin_record and admin_record.evaluated_document else None
    

class AdministrativeScreeningSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='proposal_id')
    call = serializers.CharField(source='service.name')
    orgType = serializers.CharField(source='org_type')
    orgName = serializers.SerializerMethodField()
    subject = serializers.CharField()
    description = serializers.CharField()
    status = serializers.SerializerMethodField()
    fundsRequested = serializers.SerializerMethodField()
    fundsGranted = serializers.SerializerMethodField()
    applicationDocument = serializers.SerializerMethodField()
    shortlist = serializers.SerializerMethodField()
    submissionDate = serializers.DateTimeField(source='created_at')
    contactPerson = serializers.SerializerMethodField()
    contactEmail = serializers.SerializerMethodField()
    committeeDetails = serializers.SerializerMethodField()
    technical_evaluated = serializers.SerializerMethodField()
    administrativeScreeningDocument = serializers.SerializerMethodField()
    admin_decision = serializers.SerializerMethodField()
    current_stage = serializers.SerializerMethodField()
    committee_assigned = serializers.SerializerMethodField()
    


    class Meta:
        model = FormSubmission
        fields = [
            'id','call','orgType','orgName','subject','description','status',
            'fundsRequested','fundsGranted','applicationDocument','shortlist',
            'submissionDate','contactPerson','contactEmail','committeeDetails',
            'technical_evaluated','administrativeScreeningDocument','admin_decision','current_stage','committee_assigned'
        ]

    
    def get_committee_assigned(self, obj):
        return getattr(obj, 'committee_assigned', None)


    def to_representation(self, instance):
        # Cache the latest related objects ONCE per instance using prefetch cache
        instance._latest_screening_record = (
            instance.all_screening_records[0] if getattr(instance, 'all_screening_records', []) else None
        )
        instance._latest_milestone = (
            instance.all_milestones[0] if getattr(instance, 'all_milestones', []) else None
        )
        return super().to_representation(instance)

    def get_status(self, obj):
        admin_record = getattr(obj, '_latest_screening_record', None)
        return admin_record.admin_decision if admin_record else 'pending'

    def get_orgName(self, obj):
        return getattr(obj.applicant, 'organization', '') or ''

    def get_contactPerson(self, obj):
        user = getattr(obj, 'applicant', None)
        if user:
            return getattr(user, 'full_name', '') or getattr(user, 'get_full_name', lambda: '')() or user.email
        return ''

    def get_contactEmail(self, obj):
        return obj.contact_email or ''

    def get_fundsRequested(self, obj):
        return getattr(obj, 'funds_requested', None)

    def get_fundsGranted(self, obj):
        m = getattr(obj, '_latest_milestone', None)
        return m.grant_from_ttdf if m else None

    def get_applicationDocument(self, obj):
        return obj.applicationDocument.url if hasattr(obj, 'applicationDocument') and obj.applicationDocument else None

    def get_shortlist(self, obj):
        admin_record = getattr(obj, '_latest_screening_record', None)
        return admin_record.admin_decision == 'shortlisted' if admin_record else False

    def get_technical_evaluated(self, obj):
        admin_record = getattr(obj, '_latest_screening_record', None)
        return bool(admin_record and admin_record.evaluated_document)

    def get_admin_decision(self, obj):
        admin_record = getattr(obj, '_latest_screening_record', None)
        return admin_record.admin_decision if admin_record else None

    def get_current_stage(self, obj):
        admin_record = getattr(obj, '_latest_screening_record', None)

        if not admin_record:
            return 'not_started'

        if not admin_record.evaluated_document:
            return 'awaiting_document'

        if not admin_record.admin_evaluated:
            return 'awaiting_admin_decision'

        if admin_record.admin_decision == 'shortlisted':
            technical_record = getattr(admin_record, 'technical_record', None)
            if technical_record:
                if not technical_record.technical_document:
                    return 'awaiting_technical_document'
                elif not technical_record.technical_evaluated:
                    return 'awaiting_technical_decision'
                else:
                    return 'technical_completed'
            else:
                return 'admin_shortlisted'
        else:
            return 'admin_rejected'

    def get_committeeDetails(self, obj):
        committee = (
            ScreeningCommittee.objects
            .filter(service=obj.service, committee_type='administrative')
            .select_related('head')
            .prefetch_related('members')
            .first()
        )
        if not committee:
            return None

        members = [m.user.full_name for m in committee.members.all()]
        return {
            'name': committee.name,
            'head': committee.head.full_name if committee.head else None,
            'members': members,
            'documentUploaded': bool(obj.screening_records.filter(evaluated_document__isnull=False).exists()),
            'evaluationStopped': not committee.is_active,
        }

    def get_administrativeScreeningDocument(self, obj):
        admin_record = getattr(obj, '_latest_screening_record', None)
        return admin_record.evaluated_document.url if admin_record and admin_record.evaluated_document else None

# Technical Screening
class TechnicalScreeningDashboardSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='proposal_id')
    call = serializers.CharField(source='service.name')
    orgType = serializers.CharField(source='org_type')
    orgName = serializers.SerializerMethodField()
    subject = serializers.CharField()
    description = serializers.CharField()
    status = serializers.SerializerMethodField()
    fundsRequested = serializers.SerializerMethodField()
    fundsGranted = serializers.SerializerMethodField()
    applicationDocument = serializers.SerializerMethodField()
    submissionDate = serializers.DateTimeField(source='created_at')
    contactPerson = serializers.SerializerMethodField()
    contactEmail = serializers.SerializerMethodField()
    committeeDetails = serializers.SerializerMethodField()
    administrativeScreeningDocument = serializers.SerializerMethodField()
    technical_evaluated = serializers.SerializerMethodField()
    technical_decision = serializers.SerializerMethodField()
    technicalScreeningDocument = serializers.SerializerMethodField()
    shortlist = serializers.SerializerMethodField()  # Added this field

    class Meta:
        model = FormSubmission
        fields = [
            'id','call','orgType','orgName','subject','description','status',
            'fundsRequested','fundsGranted','applicationDocument',
            'submissionDate','contactPerson','contactEmail','committeeDetails',
            'administrativeScreeningDocument','technical_evaluated','technical_decision',
            'technicalScreeningDocument','shortlist'
        ]
    
    def get_status(self, obj):
        admin_record = obj.screening_records.order_by('-cycle').first()
        technical_record = getattr(admin_record, 'technical_record', None) if admin_record else None
        return technical_record.technical_decision if technical_record else 'pending'

    def get_orgName(self, obj):
        return getattr(obj.applicant, 'organization', '') or ''

    def get_contactPerson(self, obj):
        user = getattr(obj, 'applicant', None)
        if user:
            return getattr(user, 'full_name', '') or getattr(user, 'get_full_name', lambda: '')() or user.email
        return ''

    def get_contactEmail(self, obj):
        return obj.contact_email or ''

    def get_fundsRequested(self, obj):
        return getattr(obj, 'funds_requested', None)

    def get_fundsGranted(self, obj):
        latest = obj.milestones.order_by('-created_at').first()
        return latest.grant_from_ttdf if latest else None

    def get_applicationDocument(self, obj):
        field = getattr(obj, 'applicationDocument', None)
        return field.url if field else None

    def get_shortlist(self, obj):
        """Check if proposal is shortlisted in administrative screening"""
        admin_record = obj.screening_records.order_by('-cycle').first()
        return admin_record.admin_decision == 'shortlisted' if admin_record else False

    def get_technical_evaluated(self, obj):
        """TRUE if technical document uploaded (moves to evaluated tab)"""
        admin_record = obj.screening_records.order_by('-cycle').first()
        technical_record = getattr(admin_record, 'technical_record', None) if admin_record else None
        return bool(technical_record and technical_record.technical_document)

    def get_technical_decision(self, obj):
        admin_record = obj.screening_records.order_by('-cycle').first()
        technical_record = getattr(admin_record, 'technical_record', None) if admin_record else None
        return technical_record.technical_decision if technical_record else None

    def get_committeeDetails(self, obj):
        committee = (
            ScreeningCommittee.objects
            .filter(service=obj.service, committee_type='technical')
            .first()
        )
        if not committee:
            return None

        members = [m.user.full_name for m in committee.members.all()]
        return {
            'name': committee.name,
            'head': committee.head.full_name if committee.head else None,
            'members': members,
            'documentUploaded': bool(obj.screening_records.filter(
                technical_record__technical_document__isnull=False
            ).exists()),
            'evaluationStopped': not committee.is_active,
        }

    def get_administrativeScreeningDocument(self, obj):
        admin_record = obj.screening_records.order_by('-cycle').first()
        return admin_record.evaluated_document.url if admin_record and admin_record.evaluated_document else None
    
    def get_technicalScreeningDocument(self, obj):
        admin_record = obj.screening_records.order_by('-cycle').first()
        technical_record = getattr(admin_record, 'technical_record', None) if admin_record else None
        return technical_record.technical_document.url if technical_record and technical_record.technical_document else None




# ADMIN VIEW - Administrative Screening
class AdminScreeningSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='proposal_id')
    call = serializers.CharField(source='service.name')
    orgType = serializers.CharField(source='org_type')
    orgName = serializers.SerializerMethodField()
    subject = serializers.CharField()
    description = serializers.CharField()
    fundsRequested = serializers.SerializerMethodField()
    fundsGranted = serializers.SerializerMethodField()
    applicationDocument = serializers.SerializerMethodField()
    shortlist = serializers.SerializerMethodField()
    submissionDate = serializers.DateTimeField(source='created_at')
    contactPerson = serializers.SerializerMethodField()
    contactEmail = serializers.SerializerMethodField()
    committeeDetails = serializers.SerializerMethodField()
    evaluated_document = serializers.SerializerMethodField()
    admin_evaluated = serializers.SerializerMethodField()
    admin_decision = serializers.SerializerMethodField()
    current_stage = serializers.SerializerMethodField()
    committee_assigned = serializers.SerializerMethodField()

    

    class Meta:
        model = FormSubmission
        fields = [
            'id', 'call', 'orgType', 'orgName', 'subject', 'description',
            'fundsRequested', 'fundsGranted', 'applicationDocument', 'shortlist',
            'submissionDate', 'contactPerson', 'contactEmail', 'committeeDetails',
            'evaluated_document', 'admin_evaluated', 'admin_decision', 'current_stage','committee_assigned'
        ]


    def get_committee_assigned(self, obj):
        return getattr(obj, 'committee_assigned', None)
        

    def _get_latest_screening(self, obj):
        sid = getattr(obj, 'latest_screening_id', None)
        screening_records = getattr(obj, 'screening_records', None)
        if screening_records is not None:
            # RelatedManager or list
            if hasattr(screening_records, 'all'):
                iterable = screening_records.all()
            else:
                iterable = screening_records
            for rec in iterable:
                if rec.id == sid:
                    return rec
        return None

    def _get_latest_milestone(self, obj):
        mid = getattr(obj, 'latest_milestone_id', None)
        milestones = getattr(obj, 'milestones', None)
        if milestones is not None:
            if hasattr(milestones, 'all'):
                iterable = milestones.all()
            else:
                iterable = milestones
            for ms in iterable:
                if ms.id == mid:
                    return ms
        return None

    def get_orgName(self, obj):
        return getattr(obj.applicant, 'organization', '')

    def get_contactPerson(self, obj):
        user = getattr(obj, 'applicant', None)
        if user:
            return getattr(user, 'full_name', '') or \
                   getattr(user, 'get_full_name', lambda: '')() or \
                   getattr(user, 'email', '')
        return ''

    def get_contactEmail(self, obj):
        return obj.contact_email or ''

    def get_fundsRequested(self, obj):
        return getattr(obj, 'funds_requested', None)

    def get_fundsGranted(self, obj):
        m = self._get_latest_milestone(obj)
        return getattr(m, 'grant_from_ttdf', None) if m else None

    def get_applicationDocument(self, obj):
        return obj.applicationDocument.url if obj.applicationDocument else None

    def get_shortlist(self, obj):
        rec = self._get_latest_screening(obj)
        return rec.admin_decision == 'shortlisted' if rec else False

    def get_admin_evaluated(self, obj):
        rec = self._get_latest_screening(obj)
        return bool(rec and rec.admin_evaluated)

    def get_admin_decision(self, obj):
        rec = self._get_latest_screening(obj)
        return rec.admin_decision if rec else 'pending'

    def get_evaluated_document(self, obj):
        rec = self._get_latest_screening(obj)
        return rec.evaluated_document.url if rec and rec.evaluated_document else None

    def get_current_stage(self, obj):
        rec = self._get_latest_screening(obj)
        if not rec:
            return 'not_started'
        if not rec.evaluated_document:
            return 'awaiting_document'
        if not rec.admin_evaluated:
            return 'awaiting_admin_decision'
        if rec.admin_decision == 'shortlisted':
            tech = getattr(rec, 'technical_record', None)
            if tech:
                if not tech.technical_document:
                    return 'awaiting_technical_document'
                elif not tech.technical_evaluated:
                    return 'awaiting_technical_decision'
                else:
                    return 'technical_completed'
            return 'admin_shortlisted'
        return 'admin_rejected'

    def get_committeeDetails(self, obj):
        # Use prefetched committees attached to service
        committees = getattr(obj.service, 'admin_committees', [])
        committee = committees[0] if committees else None
        if not committee:
            return None
        # screening_records may be RelatedManager or list
        screening_records = getattr(obj, 'screening_records', None)
        if screening_records is not None:
            if hasattr(screening_records, 'all'):
                sr_iter = screening_records.all()
            else:
                sr_iter = screening_records
        else:
            sr_iter = []
        return {
            'name': committee.name,
            'head': committee.head.full_name if committee.head else None,
            'members': [m.user.full_name for m in committee.members.all()],
            'documentUploaded': any(getattr(rec, 'evaluated_document', None) for rec in sr_iter),
            'evaluationStopped': not committee.is_active,
        }
    

# Technical Screening
class AdminTechnicalScreeningSerializer(serializers.ModelSerializer):
    id = serializers.CharField(
        source='screening_record.proposal.proposal_id',
        read_only=True
    )
    call = serializers.CharField(
        source='screening_record.proposal.service.name',
        read_only=True
    )
    orgType = serializers.CharField(
        source='screening_record.proposal.org_type',
        read_only=True
    )
    orgName = serializers.CharField(
        source='screening_record.proposal.applicant.organization',
        default='',
        read_only=True
    )
    subject = serializers.CharField(
        source='screening_record.proposal.subject',
        read_only=True
    )
    description = serializers.CharField(
        source='screening_record.proposal.description',
        read_only=True
    )
    fundsRequested = serializers.SerializerMethodField()
    fundsGranted = serializers.SerializerMethodField()
    shortlist = serializers.SerializerMethodField()
    submissionDate = serializers.DateTimeField(
        source='screening_record.proposal.created_at',
        read_only=True
    )
    contactPerson = serializers.SerializerMethodField()
    contactEmail = serializers.CharField(
        source='screening_record.proposal.contact_email',
        default='',
        read_only=True
    )
    committeeDetails = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    proposalDocument = serializers.SerializerMethodField()
    document = serializers.SerializerMethodField()
    technical_evaluated = serializers.BooleanField()
    administrativeDocument = serializers.SerializerMethodField()
    admin_evaluated = serializers.SerializerMethodField()

    class Meta:
        model = TechnicalScreeningRecord
        fields = [
            'id','call','orgType','orgName','subject','description',
            'fundsRequested','fundsGranted','shortlist','submissionDate',
            'contactPerson','contactEmail','committeeDetails',
            'proposalDocument','document','technical_evaluated','status','administrativeDocument','admin_evaluated',
        ]

    def get_status(self, obj):
        return getattr(obj, 'technical_decision', None)   
    
    def get_contactPerson(self, obj):
        proposal = getattr(obj.screening_record, 'proposal', None)
        user = getattr(proposal, 'applicant', None) if proposal else None
        if user:
            if hasattr(user, 'get_full_name') and callable(user.get_full_name):
             return user.get_full_name() or ''
            elif hasattr(user, 'full_name'):
             return user.full_name or ''
            elif hasattr(user, 'username'):
             return user.username or ''
            elif hasattr(user, 'email'):
             return user.email or ''
        return ''


    def get_fundsRequested(self, obj):
        fs = obj.screening_record.proposal
        m = fs.milestones.order_by('-created_at').first()
        return m.funds_requested if m else None

    def get_fundsRequested(self, obj):
        return getattr(obj, 'funds_requested', None)

    def get_shortlist(self, obj):
        rec = obj.screening_record
        return rec.admin_decision == 'shortlisted'

    def get_committeeDetails(self, obj):
        fs = obj.screening_record.proposal
        committee = ScreeningCommittee.objects.filter(
            service=fs.service,
            committee_type='technical'
        ).first()
        if not committee:
            return None
        members = [m.user.full_name for m in committee.members.all()]
        return {
            'name': committee.name,
            'head': committee.head.full_name if committee.head else None,
            'members': members,
            'documentUploaded': ScreeningRecord.objects.filter(proposal=fs).exists(),
            'evaluationStopped': not committee.is_active,
        }

    def get_proposalDocument(self, obj):
        try:
            proposal = obj.screening_record.proposal
            document = proposal.applicationDocument
            return document.url if document else None
        except Exception:
            return None
     
    def get_administrativeDocument(self, obj):
        try:
            document = obj.screening_record.evaluated_document
            return document.url if document else None
        except Exception:
            return None

    def get_document(self, obj):
        return obj.technical_document.url if obj.technical_document else None

    def get_admin_evaluated(self, obj):
        return obj.screening_record.admin_evaluated
    

