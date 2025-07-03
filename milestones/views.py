# milestones/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404
from dynamic_form.models import FormSubmission
from urllib.parse import unquote
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Milestone, SubMilestone,
    FinanceRequest, PaymentClaim, FinanceSanction ,MilestoneDocument, SubMilestoneDocument
)
from .serializers import (
    MilestoneSerializer, SubMilestoneSerializer,
    FinanceRequestSerializer, PaymentClaimSerializer,
    IAMilestoneSerializer, FinanceSanctionSerializer,
    SanctionSummarySerializer, ClaimDetailSerializer
)
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions         import IsAuthenticated

# views.py

from .serializers import (
    MilestoneSerializer, SubMilestoneSerializer,
    MilestoneDocumentSerializer, SubMilestoneDocumentSerializer
)

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404

from .models import (
    Milestone, SubMilestone, MilestoneDocument, SubMilestoneDocument, MilestoneHistory
)
from .serializers import (
    MilestoneSerializer, SubMilestoneSerializer,
    MilestoneDocumentSerializer, SubMilestoneDocumentSerializer
)

# views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ProposalMouDocument
from .serializers import ProposalMouDocumentSerializer
from dynamic_form.models import FormSubmission
from django.db import IntegrityError

class ProposalMouDocumentViewSet(viewsets.ModelViewSet):
    queryset = ProposalMouDocument.objects.all()
    serializer_class = ProposalMouDocumentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Accept proposal_id (business key) instead of pk
        proposal_id = request.data.get("proposal_id")
        if not proposal_id:
            return Response({"error": "proposal_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            proposal = FormSubmission.objects.get(proposal_id=proposal_id)
        except FormSubmission.DoesNotExist:
            return Response({"error": f"Proposal with id '{proposal_id}' does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        # Prevent duplicate
        if hasattr(proposal, 'mou_document'):
            return Response({"error": "MOU already uploaded for this proposal."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['proposal'] = proposal.pk
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response({"error": "MOU already exists for this proposal."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MilestoneViewSet(viewsets.ModelViewSet):
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Accept proposal_id from input
        proposal_id = request.data.get("proposal_id")
        if not proposal_id:
            return Response({"error": "proposal_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            proposal = FormSubmission.objects.get(proposal_id=proposal_id)
        except FormSubmission.DoesNotExist:
            return Response({"error": f"FormSubmission with proposal_id '{proposal_id}' does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data["proposal"] = proposal.pk  # Set the FK for serializer

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save(
                    created_by=request.user,
                    updated_by=request.user
                )
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            return Response({"error": f"Error creating milestone: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        try:
            serializer.save(updated_by=self.request.user)
        except Exception as e:
            raise IntegrityError(f"Error updating milestone: {str(e)}")

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            return Response({"error": f"Error deleting milestone: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='break')
    def break_into_submilestones(self, request, pk=None):
        milestone = self.get_object()
        submilestones_data = request.data.get('submilestones', [])
        if not submilestones_data:
            return Response({"error": "No submilestones data provided."}, status=400)

        created = []
        try:
            with transaction.atomic():
                # (Optional) Save snapshot here
                for sm_data in submilestones_data:
                    sm_data['milestone'] = milestone.id
                    serializer = SubMilestoneSerializer(data=sm_data)
                    serializer.is_valid(raise_exception=True)
                    instance = serializer.save(
                        created_by=request.user,
                        updated_by=request.user
                    )
                    created.append(SubMilestoneSerializer(instance).data)
            return Response({
                "message": "Milestone broken, submilestones created.",
                "submilestones": created
            }, status=201)
        except Exception as e:
            return Response({"error": f"Error breaking milestone: {str(e)}"}, status=400)

class MilestoneDocumentViewSet(viewsets.ModelViewSet):
    queryset = MilestoneDocument.objects.all()
    serializer_class = MilestoneDocumentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            raise IntegrityError(f"Error creating milestone document: {str(e)}")

    def perform_update(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            raise IntegrityError(f"Error updating milestone document: {str(e)}")

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            return Response({"error": f"Error deleting milestone document: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_document_status(self, request, pk=None):
        doc = self.get_object()
        updated = False
        valid_fields = []
        for field in ['mpr_status', 'mcr_status', 'uc_status', 'assets_status']:
            if field in request.data:
                value = request.data[field]
                if value not in dict(doc._meta.get_field(field).choices):
                    return Response(
                        {"error": f"Invalid status value '{value}' for {field}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                setattr(doc, field, value)
                updated = True
                valid_fields.append(field)
        if updated:
            try:
                doc.save()
                return Response(
                    {"message": f"Status updated for: {', '.join(valid_fields)}.", "doc": MilestoneDocumentSerializer(doc).data}
                )
            except Exception as e:
                return Response({"error": f"Error updating status: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "No valid status field found in request."}, status=status.HTTP_400_BAD_REQUEST)

class SubMilestoneViewSet(viewsets.ModelViewSet):
    queryset = SubMilestone.objects.all()
    serializer_class = SubMilestoneSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        try:
            serializer.save(created_by=self.request.user, updated_by=self.request.user)
        except Exception as e:
            raise IntegrityError(f"Error creating submilestone: {str(e)}")

    def perform_update(self, serializer):
        try:
            serializer.save(updated_by=self.request.user)
        except Exception as e:
            raise IntegrityError(f"Error updating submilestone: {str(e)}")

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            return Response({"error": f"Error deleting submilestone: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class SubMilestoneDocumentViewSet(viewsets.ModelViewSet):
    queryset = SubMilestoneDocument.objects.all()
    serializer_class = SubMilestoneDocumentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            raise IntegrityError(f"Error creating submilestone document: {str(e)}")

    def perform_update(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            raise IntegrityError(f"Error updating submilestone document: {str(e)}")

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            return Response({"error": f"Error deleting submilestone document: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_document_status(self, request, pk=None):
        doc = self.get_object()
        updated = False
        valid_fields = []
        for field in ['mpr_status', 'mcr_status', 'uc_status', 'assets_status']:
            if field in request.data:
                value = request.data[field]
                if value not in dict(doc._meta.get_field(field).choices):
                    return Response(
                        {"error": f"Invalid status value '{value}' for {field}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                setattr(doc, field, value)
                updated = True
                valid_fields.append(field)
        if updated:
            try:
                doc.save()
                return Response(
                    {"message": f"Status updated for: {', '.join(valid_fields)}.", "doc": SubMilestoneDocumentSerializer(doc).data}
                )
            except Exception as e:
                return Response({"error": f"Error updating status: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "No valid status field found in request."}, status=status.HTTP_400_BAD_REQUEST)
























class FinanceRequestViewSet(viewsets.ModelViewSet):
    """
    Supports GET, POST, PUT, PATCH, DELETE on finance requests.
    """
    queryset = FinanceRequest.objects.all()
    serializer_class = FinanceRequestSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(detail=True, methods=['post', 'patch'])
    def approve(self, request, pk=None):
        fr = self.get_object()
        if fr.status != FinanceRequest.PENDING_IA:
            return Response({"detail": "Invalid state"},
                            status=status.HTTP_400_BAD_REQUEST)
        fr.status = FinanceRequest.IA_APPROVED
        fr.ia_remark = ''
        fr.reviewed_at = timezone.now()
        fr.updated_by = request.user
        fr.save()
        return Response(FinanceRequestSerializer(fr).data)

    @action(detail=True, methods=['post', 'patch'])
    def reject(self, request, pk=None):
        remark = request.data.get('ia_remark')
        if not remark:
            return Response({"detail": "IA remark required"},
                            status=status.HTTP_400_BAD_REQUEST)
        fr = self.get_object()
        if fr.status != FinanceRequest.PENDING_IA:
            return Response({"detail": "Invalid state"},
                            status=status.HTTP_400_BAD_REQUEST)
        fr.status = FinanceRequest.IA_REJECTED
        fr.ia_remark = remark
        fr.reviewed_at = timezone.now()
        fr.updated_by = request.user
        fr.save()
        return Response(FinanceRequestSerializer(fr).data)


class PaymentClaimViewSet(viewsets.ModelViewSet):
    """
    Supports GET, POST, PUT, PATCH, DELETE on payment claims.
    """
    queryset = PaymentClaim.objects.all()
    serializer_class = PaymentClaimSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(detail=True, methods=['post', 'patch'])
    def approve(self, request, pk=None):
        pc = self.get_object()
        if pc.status != PaymentClaim.PENDING_JF:
            return Response({"detail": "Invalid state"},
                            status=status.HTTP_400_BAD_REQUEST)
        pc.status = PaymentClaim.JF_APPROVED
        pc.jf_remark = ''
        pc.reviewed_at = timezone.now()
        pc.updated_by = request.user
        pc.save()
        return Response(PaymentClaimSerializer(pc).data)

    @action(detail=True, methods=['post', 'patch'])
    def reject(self, request, pk=None):
        remark = request.data.get('jf_remark')
        if not remark:
            return Response({"detail": "JF remark required"},
                            status=status.HTTP_400_BAD_REQUEST)
        pc = self.get_object()
        if pc.status != PaymentClaim.PENDING_JF:
            return Response({"detail": "Invalid state"},
                            status=status.HTTP_400_BAD_REQUEST)
        pc.status = PaymentClaim.JF_REJECTED
        pc.jf_remark = remark
        pc.reviewed_at = timezone.now()
        pc.updated_by = request.user
        pc.save()
        return Response(PaymentClaimSerializer(pc).data)


class FinanceSanctionViewSet(viewsets.ModelViewSet):
    """
    Supports GET, POST, PUT, PATCH, DELETE on finance sanctions.
    """
    queryset = FinanceSanction.objects.all()
    serializer_class = FinanceSanctionSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class IAMilestoneViewSet(viewsets.ModelViewSet): 
    """   
    Only returns proposals with at least one Presentation where final_decision='accepted'.
    """
    serializer_class = IAMilestoneSerializer
    lookup_field = 'proposal_id'
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        # Only proposals with at least one related accepted presentation
        return FormSubmission.objects.filter(
            status=FormSubmission.SUBMITTED,
            presentations__final_decision='shortlisted'
        ).distinct()

    def get_object(self):
        obj = super().get_object()
        if obj.applicant is None:
            raise NotFound("That proposal has no applicant attached.")
        return obj


class SanctionViewSet(viewsets.ModelViewSet):
    """
    Sanction summary and standard actions.
    """
    queryset = FinanceSanction.objects.select_related(
        'proposal__service',
        'finance_request__milestone',
        'payment_claim'
    )
    serializer_class = FinanceSanctionSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(detail=False, methods=['get'], url_path=r'summary/(?P<proposal_id>[^/.]+)')
    def summary(self, request, proposal_id=None):
        qs = self.get_queryset().filter(proposal__proposal_id=proposal_id)
        serializer = SanctionSummarySerializer(qs, many=True)
        return Response(serializer.data)


class FinanceViewSet(viewsets.ModelViewSet):
    """
    Claim detail and standard actions.
    """
    queryset = FinanceSanction.objects.select_related(
        'proposal',
        'finance_request__milestone',
        'finance_request__submilestone',
        'payment_claim'
    )
    serializer_class = ClaimDetailSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'claim-detail/(?P<proposal_id>[^/.]+)')
    def claim_detail(self, request, proposal_id=None):
        sanctions = self.get_queryset().filter(proposal__proposal_id=proposal_id)
        serializer = ClaimDetailSerializer(sanctions, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def project_tracker_proposal(request):
    """
    Get project-level data for Project Tracker page
    Expects: {"proposal_id": "TTDF/6G/302"}
    Returns: subject, proposal_id, call, submission_date, status, ttdfGrant, isMouSigned
    """
    proposal_id = request.data.get('proposal_id')
    
    if not proposal_id:
        return Response(
            {'error': 'proposal_id is required in request body'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        proposal = get_object_or_404(FormSubmission, proposal_id=proposal_id)
        
        # Check if MOU is signed
        is_mou_signed = False
        if hasattr(proposal, 'mou_document') and proposal.mou_document:
            is_mou_signed = proposal.mou_document.is_mou_signed
        
        data = {
            'subject': proposal.subject or '',
            'proposal_id': proposal.proposal_id,
            'call': proposal.service.name if proposal.service else '',  # Using service name as call
            'submission_date': proposal.created_at.date(),  # Using created_at as submission date
            'status': proposal.status,
            'ttdfGrant': proposal.grants_from_ttdf or 0,  # Using grants_from_ttdf field
            'isMouSigned': is_mou_signed
        }
        
        return Response(data, status=status.HTTP_200_OK)
        
    except FormSubmission.DoesNotExist:
        return Response(
            {'error': f'Proposal with ID {proposal_id} not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def project_tracker_milestones(request):
    """
    Get milestone data for Project Tracker page
    Expects: {"proposal_id": "TTDF/6G/302"}
    Returns: milestoneName, status, amount, duration, startDate, endDate
    """
    proposal_id = request.data.get('proposal_id')
    
    if not proposal_id:
        return Response(
            {'error': 'proposal_id is required in request body'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        proposal = get_object_or_404(FormSubmission, proposal_id=proposal_id)
        milestones = proposal.milestones.all()
        
        milestone_data = []
        for milestone in milestones:
            data = {
                'milestoneName': milestone.title,
                'status': milestone.status,
                'amount': milestone.revised_grant_from_ttdf or milestone.grant_from_ttdf,
                'duration': milestone.revised_time_required or milestone.time_required,
                'startDate': milestone.start_date,
                'endDate': milestone.due_date
            }
            milestone_data.append(data)
        
        return Response(milestone_data, status=status.HTTP_200_OK)
        
    except FormSubmission.DoesNotExist:
        return Response(
            {'error': f'Proposal with ID {proposal_id} not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def project_tracker_milestone_documents(request):
    """
    Get milestone documents for Project Tracker page
    Expects: {"proposal_id": "TTDF/6G/302"}
    Returns: mcr, mpr, uc, assetsPurchased, remarks
    """
    proposal_id = request.data.get('proposal_id')
    
    if not proposal_id:
        return Response(
            {'error': 'proposal_id is required in request body'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        proposal = get_object_or_404(FormSubmission, proposal_id=proposal_id)
        milestones = proposal.milestones.all()
        
        documents_data = []
        for milestone in milestones:
            milestone_docs = milestone.documents.all()
            for doc in milestone_docs:
                data = {
                    'milestone_id': milestone.id,
                    'milestone_name': milestone.title,
                    'mcr': doc.mcr.url if doc.mcr else None,
                    'mcr_status': doc.mcr_status,
                    'mpr': doc.mpr.url if doc.mpr else None,
                    'mpr_status': doc.mpr_status,
                    'uc': doc.uc.url if doc.uc else None,
                    'uc_status': doc.uc_status,
                    'assetsPurchased': doc.assets.url if doc.assets else None,
                    'assets_status': doc.assets_status,
                    'remarks': doc.remarks or ''
                }
                documents_data.append(data)
        
        return Response(documents_data, status=status.HTTP_200_OK)
        
    except FormSubmission.DoesNotExist:
        return Response(
            {'error': f'Proposal with ID {proposal_id} not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def project_tracker_submilestone_documents(request):
    """
    Get submilestone documents for Project Tracker page
    Expects: {"proposal_id": "TTDF/6G/302"}
    Returns: mcr, mpr, uc, assetsPurchased, remarks
    """
    proposal_id = request.data.get('proposal_id')
    
    if not proposal_id:
        return Response(
            {'error': 'proposal_id is required in request body'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        proposal = get_object_or_404(FormSubmission, proposal_id=proposal_id)
        milestones = proposal.milestones.all()
        
        documents_data = []
        for milestone in milestones:
            submilestones = milestone.submilestones.all()
            for submilestone in submilestones:
                submilestone_docs = submilestone.documents.all()
                for doc in submilestone_docs:
                    data = {
                        'milestone_id': milestone.id,
                        'milestone_name': milestone.title,
                        'submilestone_id': submilestone.id,
                        'submilestone_name': submilestone.title,
                        'mcr': doc.mcr.url if doc.mcr else None,
                        'mcr_status': doc.mcr_status,
                        'mpr': doc.mpr.url if doc.mpr else None,
                        'mpr_status': doc.mpr_status,
                        'uc': doc.uc.url if doc.uc else None,
                        'uc_status': doc.uc_status,
                        'assetsPurchased': doc.assets.url if doc.assets else None,
                        'assets_status': doc.assets_status,
                        'remarks': doc.remarks or ''
                    }
                    documents_data.append(data)
        
        return Response(documents_data, status=status.HTTP_200_OK)
        
    except FormSubmission.DoesNotExist:
        return Response(
            {'error': f'Proposal with ID {proposal_id} not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
# Add these views to your milestones/views.py

from datetime import datetime
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_milestone_document(request):
    """
    Upload documents for milestones/submilestones
    For MPR: proposalId, milestoneId, subMilestoneId, documentType, description, forMonth, file
    For UC/MCR/Assets: proposalId, milestoneId, subMilestoneId, documentType, description, file
    """
    try:
        proposal_id = request.data.get('proposalId')
        milestone_id = request.data.get('milestoneId')
        submilestone_id = request.data.get('subMilestoneId')
        document_type = request.data.get('documentType')
        description = request.data.get('description', '')
        for_month = request.data.get('forMonth')  # Format: YYYY-MM
        file = request.FILES.get('file')
        
        # Validation
        if not proposal_id:
            return Response({'error': 'proposalId is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not document_type:
            return Response({'error': 'documentType is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file:
            return Response({'error': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate document type
        valid_document_types = ['monthlyProgressReport', 'monthlyComplianceReport', 'utilizationCertificate', 'assets']
        if document_type not in valid_document_types:
            return Response({'error': f'documentType must be one of: {valid_document_types}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate proposal exists
        try:
            proposal = FormSubmission.objects.get(proposal_id=proposal_id)
        except FormSubmission.DoesNotExist:
            return Response({'error': f'Proposal {proposal_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Parse forMonth for MPR documents
        mpr_month_date = None
        if document_type == 'monthlyProgressReport' and for_month:
            try:
                # Convert "2025-06" to date(2025, 6, 1)
                year, month = for_month.split('-')
                mpr_month_date = datetime(int(year), int(month), 1).date()
            except (ValueError, IndexError):
                return Response({'error': 'forMonth must be in YYYY-MM format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle submilestone documents
        if submilestone_id:
            try:
                submilestone = SubMilestone.objects.get(id=submilestone_id)
                # Get or create document record
                doc, created = SubMilestoneDocument.objects.get_or_create(submilestone=submilestone)
                
                # Map document types to model fields
                if document_type == 'monthlyProgressReport':
                    doc.mpr = file
                    doc.mpr_status = 'pending'
                    if mpr_month_date:
                        doc.mpr_for_month = mpr_month_date
                elif document_type == 'utilizationCertificate':
                    doc.uc = file
                    doc.uc_status = 'pending'
                elif document_type == 'monthlyComplianceReport':
                    doc.mcr = file
                    doc.mcr_status = 'pending'
                elif document_type == 'assets':
                    doc.assets = file
                    doc.assets_status = 'pending'
                
                doc.remarks = description
                doc.save()
                
                return Response({
                    'message': 'Document uploaded successfully',
                    'document_id': doc.id,
                    'document_type': document_type,
                    'submilestone_id': submilestone_id,
                    'for_month': for_month if document_type == 'monthlyProgressReport' else None
                }, status=status.HTTP_201_CREATED)
                
            except SubMilestone.DoesNotExist:
                return Response({'error': f'SubMilestone {submilestone_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Handle milestone documents
        elif milestone_id:
            try:
                milestone = Milestone.objects.get(id=milestone_id)
                # Get or create document record
                doc, created = MilestoneDocument.objects.get_or_create(milestone=milestone)
                
                # Map document types to model fields
                if document_type == 'monthlyProgressReport':
                    doc.mpr = file
                    doc.mpr_status = 'pending'
                    if mpr_month_date:
                        doc.mpr_for_month = mpr_month_date
                elif document_type == 'utilizationCertificate':
                    doc.uc = file
                    doc.uc_status = 'pending'
                elif document_type == 'monthlyComplianceReport':
                    doc.mcr = file
                    doc.mcr_status = 'pending'
                elif document_type == 'assets':
                    doc.assets = file
                    doc.assets_status = 'pending'
                
                doc.remarks = description
                doc.save()
                
                return Response({
                    'message': 'Document uploaded successfully',
                    'document_id': doc.id,
                    'document_type': document_type,
                    'milestone_id': milestone_id,
                    'for_month': for_month if document_type == 'monthlyProgressReport' else None
                }, status=status.HTTP_201_CREATED)
                
            except Milestone.DoesNotExist:
                return Response({'error': f'Milestone {milestone_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        else:
            return Response({'error': 'Either milestoneId or subMilestoneId is required'}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def raise_payment_claim(request):
    """
    Raise a payment claim
    Expected: proposalId, milestoneId, subMilestoneId (optional), claimAmount, notes
    """
    try:
        proposal_id = request.data.get('proposalId')
        milestone_id = request.data.get('milestoneId')
        submilestone_id = request.data.get('subMilestoneId')
        claim_amount = request.data.get('claimAmount')
        notes = request.data.get('notes', '')
        
        # Validation
        if not proposal_id:
            return Response({'error': 'proposalId is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not milestone_id:
            return Response({'error': 'milestoneId is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not claim_amount:
            return Response({'error': 'claimAmount is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            claim_amount = float(claim_amount)
            if claim_amount <= 0:
                return Response({'error': 'claimAmount must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'claimAmount must be a valid number'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate proposal exists
        try:
            proposal = FormSubmission.objects.get(proposal_id=proposal_id)
        except FormSubmission.DoesNotExist:
            return Response({'error': f'Proposal {proposal_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Validate milestone exists
        try:
            milestone = Milestone.objects.get(id=milestone_id)
        except Milestone.DoesNotExist:
            return Response({'error': f'Milestone {milestone_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Validate submilestone if provided
        submilestone = None
        if submilestone_id:
            try:
                submilestone = SubMilestone.objects.get(id=submilestone_id)
            except SubMilestone.DoesNotExist:
                return Response({'error': f'SubMilestone {submilestone_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Create payment claim
        payment_claim = PaymentClaim.objects.create(
            proposal=proposal,
            milestone=milestone,
            sub_milestone=submilestone,
            net_claim_amount=claim_amount,
            ia_remark=notes,
            ia_user=request.user,
            status=PaymentClaim.PENDING_JF,
            ia_action=PaymentClaim.PENDING_IA
        )
        
        return Response({
            'message': 'Payment claim raised successfully',
            'claim_id': payment_claim.id,
            'proposal_id': proposal_id,
            'milestone_id': milestone_id,
            'submilestone_id': submilestone_id,
            'claim_amount': claim_amount,
            'status': payment_claim.status,
            'created_at': payment_claim.created_at
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    
        


# IA

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Prefetch
from .models import ImplementationAgency
from .serializers import ImplementationAgencySerializer

class ImplementationAgencyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ImplementationAgency CRUD and proposal assignment.
    """
    queryset = ImplementationAgency.objects.all().prefetch_related('users')
    serializer_class = ImplementationAgencySerializer
    permission_classes = [IsAdminUser]   # You can relax to IsAuthenticated if you want

    # For GET /list and GET /<id>/
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # Custom action for assigning/unassigning proposals (bulk, POST)
    @action(detail=True, methods=['post'], url_path='assign-proposals')
    def assign_proposals(self, request, pk=None):
        agency = self.get_object()
        proposal_ids = request.data.get('proposal_ids', [])
        if not isinstance(proposal_ids, list):
            return Response({'error': 'proposal_ids must be a list'}, status=400)
        # Avoid duplicates
        current_set = set(agency.assigned_proposals)
        new_ids = set(proposal_ids)
        agency.assigned_proposals = list(current_set.union(new_ids))
        agency.save(update_fields=['assigned_proposals'])
        return Response({'assigned_proposals': agency.assigned_proposals})

    @action(detail=True, methods=['post'], url_path='unassign-proposals')
    def unassign_proposals(self, request, pk=None):
        agency = self.get_object()
        proposal_ids = request.data.get('proposal_ids', [])
        if not isinstance(proposal_ids, list):
            return Response({'error': 'proposal_ids must be a list'}, status=400)
        agency.assigned_proposals = [pid for pid in agency.assigned_proposals if pid not in proposal_ids]
        agency.save(update_fields=['assigned_proposals'])
        return Response({'assigned_proposals': agency.assigned_proposals})


from rest_framework.views import APIView
from presentation.models import Presentation

class ShortlistedProposalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, proposal_id):
        try:
            # Get the presentation for the given proposal_id (you can add filters like final_decision='shortlisted' if you want)
            pres = (
                Presentation.objects.only(
                    'id', 'proposal_id', 'cached_final_decision_display', 'cached_applicant_data',
                    'cached_video_url', 'cached_document_url', 'cached_status',
                    'cached_evaluator_name', 'cached_admin_name', 'cached_marks_summary',
                    'cached_is_ready_for_evaluation', 'cached_is_evaluation_completed',
                    'cached_can_make_final_decision', 'cache_updated_at', 'admin_remarks', 'evaluator_remarks'
                )
                .filter(proposal_id=proposal_id)
                .order_by('-created_at')  # Get the latest presentation for this proposal (if multiple)
                .first()
            )
            if not pres:
                return Response({'error': 'Presentation not found for proposal id'}, status=404)
        except Exception:
            return Response({'error': 'Error fetching presentation'}, status=500)

        applicant = pres.cached_applicant_data or {}

        data = {
            "presentation_id": pres.id,
            "proposal_id": pres.proposal_id,
            "final_decision": pres.cached_final_decision_display or "shortlisted",
            "applicant_name": applicant.get('name', ''),
            "applicant_email": applicant.get('email', ''),
            "organization": applicant.get('organization', ''),
            "video_url": pres.cached_video_url,
            "document_url": pres.cached_document_url,
            "evaluator": pres.cached_evaluator_name,
            "admin": pres.cached_admin_name,
            "marks_summary": pres.cached_marks_summary,
            "status": pres.cached_status,
            "is_ready_for_evaluation": pres.cached_is_ready_for_evaluation,
            "is_evaluation_completed": pres.cached_is_evaluation_completed,
            "can_make_final_decision": pres.cached_can_make_final_decision,
            "last_updated": pres.cache_updated_at,
            "admin_remarks": pres.admin_remarks,
            "evaluator_remarks": pres.evaluator_remarks,
        }
        return Response(data)




from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from presentation.models import Presentation
from dynamic_form.models import FormSubmission
from milestones.models import ImplementationAgency  # Adjust if your import path differs

class ShortlistedProposalsBasicView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Step 1: Get all shortlisted Presentations and needed fields
        presentations = (
            Presentation.objects
            .filter(final_decision='shortlisted')
            .select_related('proposal__applicant', 'proposal__service')
            .only(
                'proposal_id',
                'proposal__org_type',
                'proposal__applicant__organization',
                'proposal__subject',
                'proposal__description',
                'proposal__service__name',
                'proposal__applicant__full_name',
                'proposal__contact_email',
                'proposal__created_at',
                'proposal__applicationDocument',
            )
        )

        proposal_ids = [str(p.proposal_id) for p in presentations]

        # Step 2: Build proposal_id → IA name map (no .overlap lookup, just robust in-Python mapping)
        agencies = ImplementationAgency.objects.exclude(assigned_proposals=[])
        proposal_to_ia = {}
        for ia in agencies:
            for pid in ia.assigned_proposals:
                proposal_to_ia[str(pid)] = ia.name

        # Step 3: Fetch latest milestone for each proposal (for fundsRequested)
        milestones = (
            FormSubmission.objects
            .filter(proposal_id__in=proposal_ids)
            .prefetch_related('milestones')
        )
        funds_map = {}
        for sub in milestones:
            ms = sub.milestones.order_by('-created_at').first()
            funds_map[str(sub.proposal_id)] = ms.funds_requested if ms else None

        # Step 4: Build response
        result = []
        for pres in presentations:
            proposal = pres.proposal
            applicant = getattr(proposal, 'applicant', None)
            org_type = getattr(proposal, 'org_type', '')
            org_name = getattr(applicant, 'organization', '')
            subject = getattr(proposal, 'subject', '')
            description = getattr(proposal, 'description', '')
            call = getattr(getattr(proposal, 'service', None), 'name', '')
            contact_person = getattr(applicant, 'full_name', '') or (applicant.email if applicant else '')
            contact_email = getattr(proposal, 'contact_email', '')
            submission_date = proposal.created_at
            application_document = proposal.applicationDocument.url if getattr(proposal, 'applicationDocument', None) else None
            funds_requested = funds_map.get(str(proposal.proposal_id), None)

            # NEW: Assigned IA name and status
            assigned_ia_name = proposal_to_ia.get(str(proposal.proposal_id))
            ia_status = "assigned" if assigned_ia_name else "unassigned"

            result.append({
                "proposal_id": proposal.proposal_id,
                "orgType": org_type,
                "orgName": org_name,
                "subject": subject,
                "fundsRequested": funds_requested,
                "services": call,
                "contactPerson": contact_person,
                "contactEmail": contact_email,
                "submissionDate": submission_date,
                "description": description,
                "applicationDocument": application_document,
                "assignedIA": assigned_ia_name,
                "iaStatus": ia_status,
            })
        return Response({"shortlisted_proposals": result})
