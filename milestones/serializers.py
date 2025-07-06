# milestones/serializers.py

from rest_framework import serializers
from .models import (
    Milestone, SubMilestone,
    FinanceRequest, PaymentClaim,FinanceSanction
)
from dynamic_form.models import FormSubmission
from rest_framework import viewsets
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.generics import get_object_or_404

# serializers.py

from rest_framework import serializers
from .models import Milestone, SubMilestone, MilestoneDocument, SubMilestoneDocument

 
from .models import (
    Milestone, MilestoneDocument, SubMilestone, SubMilestoneDocument,ProposalMouDocument,
    MilestoneHistory
)

class ProposalMouDocumentSerializer(serializers.ModelSerializer):
    proposal_id = serializers.CharField(source="proposal.proposal_id", read_only=True)
    mou_document = serializers.FileField(source='document')
    class Meta:
        model = ProposalMouDocument
        fields = ['id', 'proposal', 'proposal_id', 'mou_document', 'uploaded_at']
        extra_kwargs = {'proposal': {'write_only': True}}


class MilestoneDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MilestoneDocument
        fields = [
            'id', 'milestone', 'mpr', 'mpr_status',
            'mcr', 'mcr_status', 'uc', 'uc_status',
            'assets', 'assets_status', 'uploaded_at'
        ]
        read_only_fields = ['uploaded_at']

class SubMilestoneDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubMilestoneDocument
        fields = [
            'id', 'submilestone', 'mpr', 'mpr_status',
            'mcr', 'mcr_status', 'uc', 'uc_status',
            'assets', 'assets_status', 'uploaded_at'
        ]
        read_only_fields = ['uploaded_at']

class SubMilestoneSerializer(serializers.ModelSerializer):
    documents = SubMilestoneDocumentSerializer(many=True, read_only=True)
    class Meta:
        model = SubMilestone
        fields = [
            'id', 'milestone', 'title', 'time_required', 'revised_time_required',
            'grant_from_ttdf', 'initial_contri_applicant', 'revised_contri_applicant',
            'initial_grant_from_ttdf', 'revised_grant_from_ttdf', 'description',
            'created_by', 'created_at', 'updated_by', 'updated_at', 'documents'
        ]

class MilestoneSerializer(serializers.ModelSerializer):
    # For output
    proposal_id = serializers.CharField(source="proposal.proposal_id", read_only=True)
    # For input, accept the proposal pk (set by your view, but hidden from output)
    proposal = serializers.PrimaryKeyRelatedField(
        queryset=FormSubmission.objects.all(),
        write_only=True,
        required=True
    )
    documents = MilestoneDocumentSerializer(many=True, read_only=True)
    submilestones = SubMilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = Milestone
        fields = [
            'id', 'proposal', 'proposal_id', 'title', 'time_required', 'revised_time_required',
            'grant_from_ttdf', 'initial_contri_applicant', 'revised_contri_applicant',
            'initial_grant_from_ttdf', 'revised_grant_from_ttdf', 'description',
            'agreement', 'mou_document',
            'created_by', 'created_at', 'updated_by', 'updated_at',
            'documents', 'submilestones'
        ]

class FinanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceRequest
        fields = '__all__'
        read_only_fields = [
            'applicant','status','ia_remark',
            'created_by','created_at','reviewed_at',
            'updated_by','updated_at'
        ]

    def create(self, validated_data):
        validated_data['applicant'] = self.context['request'].user
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


# class PaymentClaimSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PaymentClaim
#         fields = '__all__'
#         read_only_fields = [
#             'ia_user', 'status', 'jf_remark',
#             'created_at', 'reviewed_at', 'updated_by', 'updated_at'
#         ]

#     def validate(self, data):
#         # Use provided finance_request, or fall back to the instance (for PATCH)
#         fr = data.get('finance_request') or getattr(self.instance, 'finance_request', None)
#         if fr is None:
#             raise serializers.ValidationError({"finance_request": "FinanceRequest is required."})

#         # Defensive check for the full relation chain
#         milestone = getattr(fr, 'milestone', None)
#         if milestone is None:
#             raise serializers.ValidationError({"finance_request": "FinanceRequest must be linked to a Milestone."})

#         proposal = getattr(milestone, 'proposal', None)
#         if proposal is None:
#             raise serializers.ValidationError({"finance_request": "Milestone must be linked to a Proposal."})

#         milestones = list(proposal.milestones.order_by('created_at'))
#         idx = next((i for i, m in enumerate(milestones, start=1) if m == milestone), None)
#         is_first = (idx == 1)
#         is_second = (idx == 2)

#         if is_first:
#             if not data.get('advance_payment', getattr(self.instance, 'advance_payment', None)):
#                 raise serializers.ValidationError("First milestone must request advance_payment=True")
#             if data.get('penalty_amount', getattr(self.instance, 'penalty_amount', 0)) or \
#                data.get('adjustment_amount', getattr(self.instance, 'adjustment_amount', 0)):
#                 raise serializers.ValidationError("No penalties or adjustments on first milestone")
#         elif is_second:
#             if data.get('advance_payment', getattr(self.instance, 'advance_payment', None)):
#                 raise serializers.ValidationError("Advance payment only on first milestone")
#             if data.get('adjustment_amount', getattr(self.instance, 'adjustment_amount', 0)):
#                 raise serializers.ValidationError("Adjustments only allowed from third milestone onward")
#         # third+ milestones: penalty and adjustment allowed
#         return data

#     def create(self, validated_data):
#         validated_data['ia_user'] = self.context['request'].user
#         return super().create(validated_data)


class PaymentClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentClaim
        fields = '__all__'
        read_only_fields = [
            'ia_user', 'status', 'jf_remark',
            'created_at', 'reviewed_at', 'updated_by', 'updated_at'
        ]

    def validate(self, data):
        milestone = data.get('milestone') or getattr(self.instance, 'milestone', None)
        sub_milestone = data.get('sub_milestone') or getattr(self.instance, 'sub_milestone', None)
        
        # At least one must be set, but not both
        if not milestone and not sub_milestone:
            raise serializers.ValidationError("Either milestone or sub_milestone must be set.")
        if milestone and sub_milestone:
            raise serializers.ValidationError("Only one of milestone or sub_milestone should be set.")

        # Get the proposal for validation logic
        if milestone:
            proposal = milestone.proposal
            milestones = list(proposal.milestones.order_by('created_at'))
            idx = next((i for i, m in enumerate(milestones, start=1) if m == milestone), None)
        else:
            proposal = sub_milestone.milestone.proposal
            milestones = list(proposal.milestones.order_by('created_at'))
            # for sub-milestone, you might want to refer to its parent milestone's index
            idx = next((i for i, m in enumerate(milestones, start=1) if m == sub_milestone.milestone), None)

        is_first = (idx == 1)
        is_second = (idx == 2)

        if is_first:
            if not data.get('advance_payment', getattr(self.instance, 'advance_payment', None)):
                raise serializers.ValidationError("First milestone must request advance_payment=True")
            if data.get('penalty_amount', getattr(self.instance, 'penalty_amount', 0)) or \
               data.get('adjustment_amount', getattr(self.instance, 'adjustment_amount', 0)):
                raise serializers.ValidationError("No penalties or adjustments on first milestone")
        elif is_second:
            if data.get('advance_payment', getattr(self.instance, 'advance_payment', None)):
                raise serializers.ValidationError("Advance payment only on first milestone")
            if data.get('adjustment_amount', getattr(self.instance, 'adjustment_amount', 0)):
                raise serializers.ValidationError("Adjustments only allowed from third milestone onward")
        # third+ milestones: penalty and adjustment allowed

        return data

    def create(self, validated_data):
        validated_data['ia_user'] = self.context['request'].user
        return super().create(validated_data)




class FinanceSanctionSerializer(serializers.ModelSerializer):
    # this will appear in every response
    proposal_id = serializers.CharField(
        source='finance_request.proposal.proposal_id',
        read_only=True
    )
    net_claim_amount  = serializers.DecimalField(
        source='payment_claim.net_claim_amount',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    service_name     = serializers.CharField(
        source='finance_request.proposal.service.name',
        read_only=True
    )
    milestone_id     = serializers.IntegerField(
        source='finance_request.milestone.id',
        read_only=True
    )
    milestone_title  = serializers.CharField(
        source='finance_request.milestone.title',
        read_only=True
    )
    ia_action = serializers.CharField(
        source='payment_claim.ia_action', read_only=True
    )
    ia_remark = serializers.CharField(
        source='payment_claim.ia_remark', read_only=True
    )
    class Meta:
        model = FinanceSanction
        # '__all__' will include both model fields + any declared extra fields
        fields = '__all__'
        read_only_fields = (
            'proposal_id',
            'created_by', 'created_at', 'updated_by', 'updated_at',
            'jf_user', 'reviewed_at','net_claim_amount', 'ia_action', 'ia_remark'
        )

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")

        user = request.user
        if not user.has_role('JF'):
            raise serializers.ValidationError("You do not have permission to modify this sanction.")

        # only 'status' change stamps JF info
        if 'status' in validated_data:
            instance.status = validated_data['status']
            instance.jf_user    = user
            instance.reviewed_at = timezone.now()

        # allow these to be updated too
        instance.sanction_amount = validated_data.get('sanction_amount', instance.sanction_amount)
        instance.sanction_note   = validated_data.get('sanction_note',   instance.sanction_note)
        instance.updated_by      = user
        instance.save()
        return instance

 

class IAMilestoneSerializer(serializers.ModelSerializer): 
    primaryApplicant = serializers.CharField(source='applicant.full_name', read_only=True)
    organization = serializers.CharField(source='applicant.organization', read_only=True)
    contactEmail = serializers.EmailField(source='applicant.email', read_only=True)
    submissionDate = serializers.DateTimeField(source='created_at', read_only=True)
    milestones = MilestoneSerializer(many=True, read_only=True)
    call = serializers.CharField(source='service.name')
    subject = serializers.CharField()
    
    expected_source_contribution = serializers.SerializerMethodField()
    details_source_funding = serializers.SerializerMethodField()
    agreement_document = serializers.SerializerMethodField()

    class Meta:
        model = FormSubmission
        fields = [
            'proposal_id','agreement_document',
            'primaryApplicant', 'organization', 'contactEmail', 'expected_source_contribution',
            'submissionDate', 'milestones', 'call', 'subject', 'details_source_funding',
            
        ]
        read_only_fields = fields

    def get_expected_source_contribution(self, obj):
        if obj.expected_source_contribution is not None:
            return str(obj.expected_source_contribution)
        return None

    def get_details_source_funding(self, obj):
        if obj.details_source_funding is not None:
            return str(obj.details_source_funding)
        return None

    def get_agreement_document(self, obj):
        mou = getattr(obj, 'mou_document', None)
        if mou and mou.document:
            request = self.context.get('request')
            url = mou.document.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None


class SanctionSummarySerializer(serializers.ModelSerializer):
    proposal_id   = serializers.CharField(source='proposal.proposal_id', read_only=True)
    id            = serializers.IntegerField(read_only=True)
    call          = serializers.CharField(source='proposal.service.name', read_only=True)
    milestone_id  = serializers.IntegerField(source='finance_request.milestone.id', read_only=True)
    claim_date    = serializers.DateTimeField(source='payment_claim.created_at', read_only=True)
    # adjust `source=` below if your claim amount lives elsewhere
    claim_amount  = serializers.DecimalField(
        source='payment_claim.claim_amount',
        max_digits=12, decimal_places=2,
        read_only=True
    )
    sanction_date   = serializers.DateField(read_only=True)
    sanction_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    status          = serializers.CharField(read_only=True)
    sanction_note   = serializers.CharField(source='sanction_note', read_only=True)

    class Meta:
        model  = FinanceSanction
        fields = (
            'proposal_id', 'id', 'call', 'milestone_id',
            'claim_date', 'claim_amount',
            'sanction_date', 'sanction_amount',
            'status', 'sanction_note',
        )

from rest_framework import serializers
from .models import FinanceSanction

class ClaimDetailSerializer(serializers.Serializer):
    proposalId         = serializers.CharField(source='proposal.proposal_id', read_only=True)
    milestoneId        = serializers.IntegerField(source='finance_request.milestone.id', read_only=True)
    subMilestone       = serializers.SerializerMethodField()
    subMilestoneAmount = serializers.DecimalField(
        source='finance_request.submilestone.revised_grant_from_ttdf',
        max_digits=12, decimal_places=2,
        allow_null=True,
        read_only=True
    )
    ttdfGrant          = serializers.DecimalField(
        source='finance_request.milestone.revised_grant_from_ttdf',
        max_digits=12, decimal_places=2,
        read_only=True
    )
    contribution       = serializers.DecimalField(
        source='finance_request.milestone.revised_contri_applicant',
        max_digits=12, decimal_places=2,
        read_only=True
    )
    penalty            = serializers.DecimalField(
        source='payment_claim.penalty_amount',
        max_digits=10, decimal_places=2,
        read_only=True
    )
    adjustment         = serializers.DecimalField(
        source='payment_claim.adjustment_amount',
        max_digits=10, decimal_places=2,
        read_only=True
    )
    netClaimAmount     = serializers.SerializerMethodField()

    def get_subMilestone(self, obj):
        sub = obj.finance_request.submilestone
        # you can return id, title, or the whole object as needed
        return sub.id if sub else None

    def get_netClaimAmount(self, obj):
        claim_amt = getattr(obj.payment_claim, 'claim_amount', 0)
        return claim_amt - obj.payment_claim.penalty_amount - obj.payment_claim.adjustment_amount










# IA


from .models import ImplementationAgency

class ImplementationAgencySerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField()
    users_count = serializers.IntegerField(source='users.count', read_only=True)

    class Meta:
        model = ImplementationAgency
        fields = [
            'id', 'name', 'admin', 'admin_name', 'users', 'users_count', 'assigned_proposals'
        ]
        read_only_fields = ['users_count']

    def get_admin_name(self, obj):
        return obj.admin.get_full_name() if obj.admin else None

