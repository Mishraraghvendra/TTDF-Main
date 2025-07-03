from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Max
from django.shortcuts import get_object_or_404
from dynamic_form.models import FormSubmission
from configuration.models import Application, ScreeningCommittee, Service
from .models import ScreeningRecord, TechnicalScreeningRecord
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from milestones.models import Milestone
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import OuterRef, Subquery, Prefetch
from dynamic_form.serializers import FormSubmissionSerializer
from django.core.exceptions import FieldError
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import ScreeningRecordSerializer, TechnicalScreeningRecordSerializer,AdministrativeScreeningSerializer,TechnicalScreeningDashboardSerializer,AdminScreeningSerializer,AdminTechnicalScreeningSerializer
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from notifications.utils import send_notification


User = get_user_model()

from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrEvaluator(BasePermission):
    def has_permission(self, request, view):
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return True

        if request.method in SAFE_METHODS:
            return request.user.is_authenticated

        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True

        technical_record = getattr(obj, 'technical_record', None)
        if technical_record is None:
            return False

        return technical_record.technical_evaluator == request.user


class ScreeningRecordViewSet(viewsets.ModelViewSet):
    queryset = ScreeningRecord.objects.all().select_related('proposal')
    serializer_class = ScreeningRecordSerializer
    permission_classes = [IsAdminOrEvaluator]
    lookup_field = 'proposal_id'

    def get_object(self):
        lookup_value = self.kwargs[self.lookup_field]

        try:
            screening_record = ScreeningRecord.objects.filter(
            proposal__proposal_id=lookup_value
        ).order_by('-cycle').first()

            if screening_record is not None:
                return screening_record

        # Try to create it if proposal exists
            proposal = get_object_or_404(FormSubmission, proposal_id=lookup_value)
            screening_record, _ = ScreeningRecord.get_or_create_for_proposal(
            proposal=proposal,
            admin_decision='pending'
        )
            return screening_record

        except FormSubmission.DoesNotExist:
            raise NotFound(f"No proposal with ID: {lookup_value}")
        except Exception as e:
            raise NotFound(f"Error retrieving screening record: {str(e)}")
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return qs

        return qs.filter(technical_record__technical_evaluator=user)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """Handle both ID and proposal_id based updates"""
        instance = self.get_object()
        
        # Update admin decision and mark as evaluated
        if 'admin_decision' in request.data:
            instance.admin_decision = request.data['admin_decision']
            instance.admin_evaluated = True
            instance.admin_evaluator = request.user
            instance.save()
            
            # Create technical screening record if shortlisted
            if instance.admin_decision == 'shortlisted':
                TechnicalScreeningRecord.objects.get_or_create(
                    screening_record=instance,
                    defaults={'technical_decision': 'pending'}
                )

            # Notify applicant
        send_notification(
            recipient=instance.proposal.applicant,
            message=f"Your proposal ({instance.proposal.proposal_id}) was {instance.admin_decision} in administrative screening.",
            notification_type="admin_screening_result"
            )
            # Notify admin (or evaluator who took action)
        send_notification(
            recipient=request.user,
            message=f"You have {instance.admin_decision} the proposal ({instance.proposal.proposal_id}) as admin.",
            notification_type="admin_screening_action"
)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)

    def perform_create(self, serializer):
        tech_rec = serializer.save(technical_evaluator=self.request.user)
        sr = tech_rec.screening_record
        sr.technical_evaluated = True
        sr.save()

    @action(
        detail=False,
        methods=['patch'],
        url_path=r'(?P<project_code>[^/]+)/(?P<year>\d{4})/(?P<record_id>[^/]+)'
    )
    def patch_by_proposal_id(self, request, project_code, year, record_id):
        proposal_id = f"{project_code}/{year}/{record_id}"
        try:
            # Get the latest record for this proposal
            record = ScreeningRecord.objects.filter(
                proposal__proposal_id=proposal_id
            ).order_by('-cycle').first()
            
            if not record:
                return Response({'detail': 'ScreeningRecord not found.'}, status=404)
        except Exception as e:
            return Response({'detail': f'Error: {str(e)}'}, status=404)

        self.check_object_permissions(request, record)

        serializer = self.get_serializer(record, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


# @method_decorator(cache_page(60 * 60 * 2), name='dispatch')
class TechnicalScreeningRecordViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TechnicalScreeningRecordSerializer

    def get_queryset(self):
        qs = TechnicalScreeningRecord.objects.select_related(
            'screening_record__proposal'
        )
        user = self.request.user

        if user.is_staff:
            return qs

        if getattr(user, 'is_evaluator', False):
            return qs.filter(technical_evaluator=user)

        return qs.filter(screening_record__proposal__applicant=user)

    @action(
        detail=False,
        methods=['get', 'patch'],
        url_path=r'(?P<project_code>[^/]+)/(?P<year>\d{4})/(?P<record_id>[^/]+)'
    )
    def by_proposal(self, request, project_code, year, record_id):
        """
        GET or PATCH /api/screening/technicalrecords/{project_code}/{year}/{record_id}/
        """
        pid = f"{project_code}/{year}/{record_id}"

        try:
            tech = self.get_queryset().get(
                screening_record__proposal__proposal_id=pid
            )
        except TechnicalScreeningRecord.DoesNotExist:
            raise NotFound(f"No technical‐screening record for proposal '{pid}'")

        if request.method == 'PATCH':
            serializer = self.get_serializer(tech, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            serializer = self.get_serializer(tech)

        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(technical_evaluator=self.request.user)


# @method_decorator(cache_page(60 * 60 * 2), name='dispatch')
class AdministrativeScreeningViewSet(viewsets.ModelViewSet):
    serializer_class = AdministrativeScreeningSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        # Prefetch only the latest screening record and milestone for efficiency
        from django.db.models import Prefetch

        return (
            FormSubmission.objects.filter(status=FormSubmission.SUBMITTED)
            .select_related('applicant', 'service')
            .prefetch_related(
                Prefetch(
                    'screening_records',
                    queryset=ScreeningRecord.objects.order_by('-cycle'),
                    to_attr='all_screening_records'
                ),
                Prefetch(
                    'milestones',
                    queryset=Milestone.objects.order_by('-created_at'),
                    to_attr='all_milestones'
                ),
            )
        )

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
        except FieldError as fe:
            return Response({
                "success": False,
                "message": "Invalid request parameters.",
                "error": str(fe)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({
                "success": False,
                "message": "Could not fetch evaluator dashboard.",
                "error": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                "success": True,
                "data": serializer.data
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        })

    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='upload-document')
    def upload_document(self, request):
        """Upload document ONLY for proposals that are truly pending (no document uploaded yet)"""
        call_name = request.data.get('call_name')
        document = request.FILES.get('document')
        
        if not call_name or not document:
            return Response(
                {'error': 'call_name and document are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = Service.objects.filter(name=call_name).first()
            if not service:
                return Response(
                    {'error': f'Call/Service not found: {call_name}'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get proposals that are truly "pending" - those that appear in the "Pending" tab
            all_proposals = FormSubmission.objects.filter(
                service=service, 
                status=FormSubmission.SUBMITTED
            )
            
            pending_proposals = list(all_proposals)
            
            if not pending_proposals:
                return Response(
                    {'error': f'No pending proposals found for call: {call_name}. All proposals may already have documents uploaded.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            created_records = []
            updated_records = []
            
            for proposal in pending_proposals:
                existing_record = proposal.screening_records.order_by('-cycle').first()
                
                if existing_record:
                    # Update existing record 
                    existing_record.evaluated_document = document
                    existing_record.admin_evaluator = request.user
                    # DO NOT change admin_decision or admin_evaluated - keep existing values
                    existing_record.save()
                    updated_records.append(existing_record.id)
                    
                elif not existing_record:
                    # Create new record for proposals without any screening record
                    new_record, created = ScreeningRecord.get_or_create_for_proposal(
                        proposal=proposal,
                        evaluated_document=document,
                        admin_evaluator=request.user,
                        admin_decision='pending'  # Only set to pending for new records
                    )
                    if created:
                        created_records.append(new_record.id)
                    else:
                        # If record was created by get_or_create but not "created" (rare edge case)
                        if not new_record.evaluated_document:
                            new_record.evaluated_document = document
                            new_record.admin_evaluator = request.user
                            new_record.save()
                            updated_records.append(new_record.id)
            
            return Response({
                'success': True,
                'message': f'Document uploaded successfully for {len(pending_proposals)} pending proposals in call: {call_name}',
                'call_name': call_name,
                'total_pending_proposals': len(pending_proposals),
                'records_created': len(created_records),
                'records_updated': len(updated_records),
                'document_name': document.name,
                'note': ''
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Upload failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @transaction.atomic
    @action(detail=False, methods=['patch'], url_path='update-status')
    def update_status(self, request):
        """Update proposal status (shortlist/reject) - for evaluators"""
        proposal_id = request.data.get('proposal_id')
        decision = request.data.get('decision')
        
        if not proposal_id or not decision:
            return Response(
                {'error': 'proposal_id and decision are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            proposal = FormSubmission.objects.get(proposal_id=proposal_id)
            screening_record = proposal.screening_records.order_by('-cycle').first()
            
            if not screening_record:
                return Response(
                    {'error': 'No screening record found for this proposal'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Update the screening record
            screening_record.admin_decision = decision
            screening_record.admin_evaluated = True
            screening_record.admin_evaluator = request.user
            screening_record.save()
            
            # Notify applicant
            send_notification(
                recipient=proposal.applicant,
                message=f"Your proposal ({proposal.proposal_id}) was {decision} in administrative screening.",
                notification_type="admin_screening_result"
            )
            # Notify acting user (admin/evaluator)
            send_notification(
                recipient=request.user,
                message=f"You have {decision} the proposal ({proposal.proposal_id}).",
                notification_type="admin_screening_action"
            )


            return Response({
                'success': True,
                'message': f'Proposal {decision} successfully',
                'proposal_id': proposal_id,
                'decision': decision
            }, status=status.HTTP_200_OK)
            
        except FormSubmission.DoesNotExist:
            return Response(
                {'error': 'Proposal not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Update failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Updated TechnicalScreeningDashboardViewSet class
# @method_decorator(cache_page(60 * 60 * 2), name='dispatch')
class TechnicalScreeningDashboardViewSet(viewsets.ModelViewSet):
    """
    GET /api/screening/technical/ → submissions ready for technical screening
    """
    serializer_class = TechnicalScreeningDashboardSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        # Only show proposals that are shortlisted in administrative screening
        # AND have technical screening records created
        return FormSubmission.objects.filter(
            screening_records__admin_decision='shortlisted',
            screening_records__admin_evaluated=True,
            screening_records__technical_record__isnull=False
        ).distinct()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
                
        except FieldError as fe:
            return Response({
                "success": False,
                "message": "Invalid request parameters.",
                "error": str(fe)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({
                "success": False,
                "message": "Could not fetch technical screening dashboard.",
                "error": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                "success": True,
                "data": serializer.data
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        })

    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='upload-document')
    def upload_technical_document(self, request):
        """Upload technical document ONLY for proposals that are truly pending technical evaluation"""
        call_name = request.data.get('call_name')
        document = request.FILES.get('document')
        
        if not call_name or not document:
            return Response(
                {'error': 'call_name and document are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = Service.objects.filter(name=call_name).first()
            if not service:
                return Response(
                    {'error': f'Call/Service not found: {call_name}'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get proposals that are truly "pending" in technical screening
            # These are shortlisted proposals with technical records but no technical document yet
            pending_technical_proposals = []
            
            shortlisted_proposals = FormSubmission.objects.filter(
                service=service,
                screening_records__admin_decision='shortlisted',
                screening_records__admin_evaluated=True,
                screening_records__technical_record__isnull=False
            ).distinct()
            
            for proposal in shortlisted_proposals:
                admin_record = proposal.screening_records.order_by('-cycle').first()
                technical_record = getattr(admin_record, 'technical_record', None)
                
                # Include in pending if technical record exists but no technical document uploaded
                if technical_record:
                    pending_technical_proposals.append(proposal)
            
            if not pending_technical_proposals:
                return Response(
                    {'error': f'No pending technical proposals found for call: {call_name}. All may already have technical documents uploaded.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            updated_records = []
            
            for proposal in pending_technical_proposals:
                admin_record = proposal.screening_records.order_by('-cycle').first()
                technical_record = getattr(admin_record, 'technical_record', None)
                
                if technical_record and not technical_record.technical_document:
                    technical_record.technical_document = document
                    technical_record.technical_evaluator = request.user
                    # DO NOT change technical_decision or technical_evaluated - keep existing values
                    technical_record.save()
                    updated_records.append(technical_record.id)
            
            return Response({
                'success': True,
                'message': f'Technical document uploaded successfully for {len(pending_technical_proposals)} pending technical proposals in call: {call_name}',
                'call_name': call_name,
                'total_pending_technical_proposals': len(pending_technical_proposals),
                'records_updated': len(updated_records),
                'document_name': document.name,
                'note': 'Only proposals without existing technical documents were affected. Previously evaluated technical proposals remain unchanged.'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Technical upload failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    @action(detail=False, methods=['patch'], url_path='update-technical-status')
    def update_technical_status(self, request):
        """
        Update technical screening status and create TechnicalEvaluationRound if shortlisted.
        """
        proposal_id = request.data.get('proposal_id')
        decision = request.data.get('decision')

        if not proposal_id or not decision:
            return Response(
                {'error': 'proposal_id and decision are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            proposal = FormSubmission.objects.get(proposal_id=proposal_id)
            screening_record = proposal.screening_records.order_by('-cycle').first()
            technical_record = getattr(screening_record, 'technical_record', None)

            if not technical_record:
                return Response(
                    {'error': 'No technical screening record found for this proposal'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update technical screening record
            technical_record.technical_decision = decision
            technical_record.technical_evaluated = True
            technical_record.technical_evaluator = request.user
            technical_record.save()

            send_notification(
                recipient=screening_record.proposal.applicant,
                message=f"Your proposal ({proposal.proposal_id}) was {technical_record.technical_decision} in technical screening.",
                notification_type="technical_screening_result"
            )
            send_notification(
                recipient=request.user,
                message=f"You have {technical_record.technical_decision} the proposal ({proposal.proposal_id}) as technical evaluator.",
                notification_type="technical_screening_action"
)


            # CREATE TechnicalEvaluationRound if shortlisted
            evaluation_round_created = False
            evaluation_round_error = None
            
            if decision == 'shortlisted':
                try:
                    # Import inside try block to handle import errors gracefully
                    from tech_eval.models import TechnicalEvaluationRound
                    
                    # Check if evaluation round already exists
                    existing_round = TechnicalEvaluationRound.objects.filter(proposal=proposal).first()
                    
                    if existing_round:
                        evaluation_round_created = True  # Already exists
                        evaluation_round_error = f"TechnicalEvaluationRound already exists (ID: {existing_round.id})"
                    else:
                        # Debug info about the user creating the round - safely handle custom User model
                        user_info = {
                            'id': request.user.id,
                            'email': getattr(request.user, 'email', 'N/A'),
                            'full_name': getattr(request.user, 'full_name', 'N/A'),
                            'is_staff': getattr(request.user, 'is_staff', False),
                            'is_superuser': getattr(request.user, 'is_superuser', False),
                            'is_active': getattr(request.user, 'is_active', True),
                            'is_admin': getattr(request.user, 'is_admin', False),
                            'is_evaluator': getattr(request.user, 'is_evaluator', False),
                        }
                        
                        # Check user roles using your custom role system
                        user_roles = []
                        try:
                            if hasattr(request.user, 'roles'):
                                user_roles = list(request.user.roles.values_list('name', flat=True))
                        except Exception:
                            user_roles = []
                        
                        # Create new evaluation round with assigned_by
                        evaluation_round = TechnicalEvaluationRound.objects.create(
                            proposal=proposal,
                            assignment_status='pending',
                            assigned_by=request.user  # Set the user who created it
                        )
                        evaluation_round_created = True
                        
                        # Debug success message
                        evaluation_round_error = f"Successfully created by user: {user_info}, roles: {user_roles}, round_id: {evaluation_round.id}"
                        
                except ImportError as e:
                    evaluation_round_error = f"TechnicalEvaluationRound model import failed: {str(e)}"
                except Exception as e:
                    # Get detailed error information
                    error_type = type(e).__name__
                    error_message = str(e)
                    
                    # Check for specific database constraint errors
                    if 'unique constraint' in error_message.lower() or 'duplicate' in error_message.lower():
                        evaluation_round_error = f"Database constraint error - round may already exist: {error_message}"
                    else:
                        evaluation_round_error = f"Failed to create TechnicalEvaluationRound ({error_type}): {error_message}"

            # Prepare response message
            if decision == 'shortlisted':
                if evaluation_round_created and not evaluation_round_error.startswith("Database constraint error"):
                    message = f'Proposal shortlisted successfully and moved to technical evaluation'
                else:
                    message = f'Proposal shortlisted successfully. Technical evaluation round status: {evaluation_round_error}'
            else:
                message = f'Proposal {decision} successfully'

            return Response({
                'success': True,
                'message': message,
                'proposal_id': proposal_id,
                'decision': decision,
                'evaluation_round_created': evaluation_round_created,
                'evaluation_round_error': evaluation_round_error,
                'user_info': {
                    'id': request.user.id,
                    'email': request.user.email,
                    'full_name': request.user.full_name,
                    'is_staff': request.user.is_staff,
                    'is_superuser': request.user.is_superuser,
                    'is_admin': request.user.is_admin,
                    'is_evaluator': request.user.is_evaluator,
                } if decision == 'shortlisted' else None
            }, status=status.HTTP_200_OK)

        except FormSubmission.DoesNotExist:
            return Response(
                {'error': 'Proposal not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Technical update failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ADMIN VIEWS

# @method_decorator(cache_page(60 * 60 * 2), name='dispatch')
class AdminScreeningViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminScreeningSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from screening.models import ScreeningRecord
        from milestones.models import Milestone
        from configuration.models import ScreeningCommittee

        # Subquery to get latest ScreeningRecord and Milestone for each FormSubmission
        latest_screening = ScreeningRecord.objects.filter(
            proposal=OuterRef('pk')
        ).order_by('-cycle').values('id')[:1]
        latest_milestone = Milestone.objects.filter(
            proposal=OuterRef('pk')
        ).order_by('-created_at').values('id')[:1]

        # Prefetch committees for all services (for committeeDetails)
        admin_committees = ScreeningCommittee.objects.filter(
            committee_type='administrative'
        ).select_related('head').prefetch_related('members__user')

        return (
            FormSubmission.objects
            .filter(status=FormSubmission.SUBMITTED)
            .select_related('service', 'applicant')
            .prefetch_related(
                Prefetch(
                    'screening_records',
                    queryset=ScreeningRecord.objects.select_related('technical_record')
                ),
                'milestones',
                Prefetch(
                    'service__screening_committees',
                    queryset=admin_committees,
                    to_attr='admin_committees'  # custom attribute for fast access
                ),
            )
            .annotate(
                latest_screening_id=Subquery(latest_screening),
                latest_milestone_id=Subquery(latest_milestone)
            )
        )

# @method_decorator(cache_page(60 * 60 * 2), name='dispatch')
class AdminTechnicalScreeningViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/screening/admintechnical/ 
    Returns each technical‐screening record with its proposalDocument and technical document
    """
    queryset = TechnicalScreeningRecord.objects.select_related(        
        'screening_record',
        'screening_record__proposal',
        'screening_record__proposal__service',
        'screening_record__proposal__applicant',
    )
    serializer_class = AdminTechnicalScreeningSerializer
    permission_classes = [IsAuthenticated]



# EVALUATOR VIEWS
# class AdministrativeScreeningViewSet(viewsets.ModelViewSet):
#     serializer_class = AdministrativeScreeningSerializer
#     permission_classes = [IsAuthenticated]
#     parser_classes = [MultiPartParser, FormParser]

#     def get_queryset(self):
#         return FormSubmission.objects.filter(status=FormSubmission.SUBMITTED)

#     def list(self, request, *args, **kwargs):
#         try:
#             queryset = self.filter_queryset(self.get_queryset())
#         except FieldError as fe:
#             return Response({
#                 "success": False,
#                 "message": "Invalid request parameters.",
#                 "error": str(fe)
#             }, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as exc:
#             return Response({
#                 "success": False,
#                 "message": "Could not fetch evaluator dashboard.",
#                 "error": str(exc)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         page = self.paginate_queryset(queryset)
#         if page is not None:
#             serializer = self.get_serializer(page, many=True)
#             return self.get_paginated_response({
#                 "success": True,
#                 "data": serializer.data
#             })

#         serializer = self.get_serializer(queryset, many=True)
#         return Response({
#             "success": True,
#             "data": serializer.data
#         })

#     @transaction.atomic
#     @action(detail=False, methods=['post'], url_path='upload-document')
#     def upload_document(self, request):
#         """Upload document ONLY for proposals that are truly pending (no document uploaded yet)"""
#         call_name = request.data.get('call_name')
#         document = request.FILES.get('document')
        
#         if not call_name or not document:
#             return Response(
#                 {'error': 'call_name and document are required'}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             service = Service.objects.filter(name=call_name).first()
#             if not service:
#                 return Response(
#                     {'error': f'Call/Service not found: {call_name}'}, 
#                     status=status.HTTP_404_NOT_FOUND
#                 )
            
#             # Get proposals that are truly "pending" - those that appear in the "Pending" tab
#             # These are proposals that either:
#             # 1. Have no screening record at all, OR
#             # 2. Have a screening record but no evaluated_document uploaded yet
#             pending_proposals = []
            
#             all_proposals = FormSubmission.objects.filter(
#                 service=service, 
#                 status=FormSubmission.SUBMITTED
#             )
            
#             for proposal in all_proposals:
#                 latest_record = proposal.screening_records.order_by('-cycle').first()
                
#                 # Include in pending if:
#                 # 1. No screening record exists, OR
#                 # 2. Screening record exists but no document uploaded (evaluated_document is None)
#                 # Remove filtering logic — include all proposals in the selected call
#                 pending_proposals = list(all_proposals)

            
#             if not pending_proposals:
#                 return Response(
#                     {'error': f'No pending proposals found for call: {call_name}. All proposals may already have documents uploaded.'}, 
#                     status=status.HTTP_404_NOT_FOUND
#                 )
            
#             created_records = []
#             updated_records = []
            
#             for proposal in pending_proposals:
#                 existing_record = proposal.screening_records.order_by('-cycle').first()
                
#                 if existing_record :
#                     # Update existing record 
#                     existing_record.evaluated_document = document
#                     existing_record.admin_evaluator = request.user
#                     # DO NOT change admin_decision or admin_evaluated - keep existing values
#                     existing_record.save()
#                     updated_records.append(existing_record.id)
                    
#                 elif not existing_record:
#                     # Create new record for proposals without any screening record
#                     new_record, created = ScreeningRecord.get_or_create_for_proposal(
#                         proposal=proposal,
#                         evaluated_document=document,
#                         admin_evaluator=request.user,
#                         admin_decision='pending'  # Only set to pending for new records
#                     )
#                     if created:
#                         created_records.append(new_record.id)
#                     else:
#                         # If record was created by get_or_create but not "created" (rare edge case)
#                         if not new_record.evaluated_document:
#                             new_record.evaluated_document = document
#                             new_record.admin_evaluator = request.user
#                             new_record.save()
#                             updated_records.append(new_record.id)
            
#             return Response({
#                 'success': True,
#                 'message': f'Document uploaded successfully for {len(pending_proposals)} pending proposals in call: {call_name}',
#                 'call_name': call_name,
#                 'total_pending_proposals': len(pending_proposals),
#                 'records_created': len(created_records),
#                 'records_updated': len(updated_records),
#                 'document_name': document.name,
#                 'note': ''
#             }, status=status.HTTP_201_CREATED)
            
#         except Exception as e:
#             return Response(
#                 {'error': f'Upload failed: {str(e)}'}, 
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

#     @transaction.atomic
#     @action(detail=False, methods=['patch'], url_path='update-status')
#     def update_status(self, request):
#         """Update proposal status (shortlist/reject) - for evaluators"""
#         proposal_id = request.data.get('proposal_id')
#         decision = request.data.get('decision')
        
#         if not proposal_id or not decision:
#             return Response(
#                 {'error': 'proposal_id and decision are required'}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             proposal = FormSubmission.objects.get(proposal_id=proposal_id)
#             screening_record = proposal.screening_records.order_by('-cycle').first()
            
#             if not screening_record:
#                 return Response(
#                     {'error': 'No screening record found for this proposal'}, 
#                     status=status.HTTP_404_NOT_FOUND
#                 )
            
#             # Update the screening record
#             screening_record.admin_decision = decision
#             screening_record.admin_evaluated = True
#             screening_record.admin_evaluator = request.user
#             screening_record.save()
            
#             return Response({
#                 'success': True,
#                 'message': f'Proposal {decision} successfully',
#                 'proposal_id': proposal_id,
#                 'decision': decision
#             }, status=status.HTTP_200_OK)
            
#         except FormSubmission.DoesNotExist:
#             return Response(
#                 {'error': 'Proposal not found'}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )
#         except Exception as e:
#             return Response(
#                 {'error': f'Update failed: {str(e)}'}, 
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
