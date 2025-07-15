# tech_eval/views.py - 

from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
from django.db.models import Q, Prefetch
import time
import logging
from rest_framework.views import APIView
from notifications.utils import send_notification

from .models import TechnicalEvaluationRound, EvaluatorAssignment, CriteriaEvaluation
from .serializers import (
    LightningFastTechnicalEvaluationRoundSerializer,LightningFastEvaluatorAssignmentSerializer,LightningFastCriteriaEvaluationSerializer,
    SuperFastAdminListSerializer,FastEvaluatorUserSerializer,FastAppEvalCriteriaSerializer
)


User = get_user_model()
logger = logging.getLogger(__name__)

class TechnicalEvaluationRoundViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LightningFastTechnicalEvaluationRoundSerializer

    def _is_admin_user(self, user):
        return (
            getattr(user, 'is_staff', False) or 
            getattr(user, 'is_superuser', False) or 
            getattr(user, 'is_admin', False) or
            (hasattr(user, 'has_role') and (
                user.has_role('Admin') or 
                user.has_role('SuperAdmin') or
                user.has_role('Technical_Admin') or 
                user.has_role('TTDF Admin')
            ))
        )

    def _is_evaluator_user(self, user):
        return (
            getattr(user, 'is_evaluator', False) or
            (hasattr(user, 'has_role') and (
                user.has_role('Evaluator') or
                user.has_role('Technical_Evaluator')
            ))
        )

    def get_queryset(self):
        """Optimized queryset with CORRECT FormSubmission fields"""
        return (
            TechnicalEvaluationRound.objects
            .select_related('proposal', 'proposal__applicant', 'proposal__service')
            .only(
                # Core fields
                'id', 'assignment_status', 'overall_decision', 'created_at', 'updated_at',
                # Cached fields
                'cached_assigned_count', 'cached_completed_count', 'cached_average_percentage',
                'cached_marks_summary', 'cached_evaluator_data', 'cached_proposal_data',
                # FormSubmission fields (actual model fields)
                'proposal__id', 'proposal__proposal_id', 'proposal__subject', 'proposal__description',
                'proposal__org_type', 'proposal__org_address_line1', 'proposal__contact_name',
                'proposal__contact_email', 'proposal__org_mobile', 'proposal__current_trl',
                'proposal__grants_from_ttdf', 'proposal__applicationDocument', 'proposal__created_at',
                # Service fields
                'proposal__service__name',
                # User fields (applicant)
                'proposal__applicant__id', 'proposal__applicant__full_name', 
                'proposal__applicant__email', 'proposal__applicant__organization'
            )
            .order_by('-created_at')
        )

    def _safe_get_attribute(self, obj, attr_path, default='N/A'):
        """Safely get nested attributes with error handling"""
        try:
            attrs = attr_path.split('.')
            value = obj
            for attr in attrs:
                if hasattr(value, attr):
                    value = getattr(value, attr)
                else:
                    return default
            return value if value is not None else default
        except Exception:
            return default

    def _get_document_url(self, proposal):
        """Get correct document URL - FIXES MEDIA PATH ISSUE"""
        try:
            if proposal and proposal.applicationDocument:
                # Get the file path from the FileField
                file_path = str(proposal.applicationDocument)
                
                # Remove 'media/' prefix if it exists (double media issue)
                if file_path.startswith('media/'):
                    file_path = file_path[6:]  # Remove 'media/' prefix
                
                # Ensure it starts with correct path structure
                if not file_path.startswith('/'):
                    file_path = '/' + file_path
                
                # Return the URL (Django will handle MEDIA_URL prefix)
                return f"/media{file_path}"
            return None
        except Exception as e:
            logger.warning(f"Error getting document URL: {e}")
            return None

    @action(detail=False, methods=['get'], url_path='admin-list')
    def admin_list(self, request):
        """Lightning-fast admin list WITHOUT pagination"""
        if not self._is_admin_user(request.user):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            start_time = time.time()
            
            # Get queryset using cached fields
            queryset = self.get_queryset()
            
            # Serialize all data without pagination
            serialized_data = self._lightning_fast_serialize(queryset)
            
            # Simple response format that matches your frontend
            response_data = {
                'success': True, 
                'data': serialized_data,
                'count': len(serialized_data)
            }
            
            elapsed = time.time() - start_time
            logger.info(f"Admin list API responded in {elapsed:.3f} seconds for {len(serialized_data)} items")
            
            return Response(response_data)

        except Exception as e:
            logger.error(f"Error in admin_list: {e}")
            return Response(
                {'error': f'Failed to fetch data: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _lightning_fast_serialize(self, queryset):
        """Ultra-fast serialization using CORRECT FormSubmission fields"""
        
        # Get milestone data
        proposal_ids = []
        for item in queryset:
            try:
                if item.proposal and hasattr(item.proposal, 'id'):
                    proposal_ids.append(item.proposal.id)
            except Exception:
                pass
        
        milestone_data = {}
        if proposal_ids:
            try:
                from milestones.models import Milestone
                milestones = Milestone.objects.filter(
                    proposal_id__in=proposal_ids
                ).values('proposal_id', 'funds_requested').order_by('proposal_id', 'created_at')
                
                for milestone in milestones:
                    if milestone['proposal_id'] not in milestone_data:
                        milestone_data[milestone['proposal_id']] = milestone['funds_requested'] or 0
            except Exception as e:
                logger.warning(f"Could not fetch milestone data: {e}")

        # Serialization using actual FormSubmission fields
        serialized_data = []
        for item in queryset:
            try:
                # Use cached data if available
                if item.cached_proposal_data:
                    proposal_data = item.cached_proposal_data
                else:
                    # Extract from FormSubmission using ACTUAL model fields
                    proposal = item.proposal
                    if proposal:
                        # Get applicant data
                        applicant = proposal.applicant if proposal.applicant else None
                        applicant_name = 'N/A'
                        applicant_email = 'N/A'
                        applicant_org = 'N/A'
                        
                        if applicant:
                            applicant_name = getattr(applicant, 'full_name', '').strip() or 'N/A'
                            applicant_email = getattr(applicant, 'email', '') or 'N/A'
                            applicant_org = getattr(applicant, 'organization', '').strip() or 'N/A'
                        
                        # Get service name
                        service_name = 'N/A'
                        if proposal.service:
                            service_name = getattr(proposal.service, 'name', 'N/A')
                        
                        proposal_data = {
                            'proposal_id': getattr(proposal, 'proposal_id', 'N/A'),
                            'call': service_name,
                            'org_type': getattr(proposal, 'org_type', None) or 'N/A',
                            'subject': getattr(proposal, 'subject', None) or 'N/A',
                            'description': getattr(proposal, 'description', None) or 'N/A',
                            
                            # Organization: prefer User.organization, fallback to FormSubmission.org_address_line1
                            'org_name': (
                                applicant_org if applicant_org != 'N/A' else 
                                getattr(proposal, 'org_address_line1', None) or 'N/A'
                            ),
                            
                            # Contact person: prefer User.full_name, fallback to FormSubmission.contact_name
                            'contact_person': (
                                applicant_name if applicant_name != 'N/A' else 
                                getattr(proposal, 'contact_name', None) or 'N/A'
                            ),
                            
                            # Contact email: prefer User.email, fallback to FormSubmission.contact_email
                            'contact_email': (
                                applicant_email if applicant_email != 'N/A' else 
                                getattr(proposal, 'contact_email', None) or 'N/A'
                            ),
                            
                            'contact_phone': getattr(proposal, 'org_mobile', None) or 'N/A',
                            'current_trl': getattr(proposal, 'current_trl', None),
                        }
                    else:
                        # Fallback if no proposal
                        proposal_data = {
                            'proposal_id': 'N/A',
                            'call': 'N/A',
                            'org_type': 'N/A',
                            'subject': 'N/A',
                            'description': 'N/A',
                            'org_name': 'N/A',
                            'contact_person': 'N/A',
                            'contact_email': 'N/A',
                            'contact_phone': 'N/A',
                            'current_trl': None,
                        }

                # Build response data
                item_data = {
                    'id': item.id,
                    'proposal_id': proposal_data.get('proposal_id', 'N/A'),
                    'call': proposal_data.get('call', 'N/A'),
                    'orgType': proposal_data.get('org_type', 'N/A'),
                    'orgName': proposal_data.get('org_name', 'N/A'),
                    'subject': proposal_data.get('subject', 'N/A'),
                    'description': proposal_data.get('description', 'N/A')[:200] + ('...' if len(proposal_data.get('description', '')) > 200 else ''),
                    'fundsRequested': (
                            getattr(item.proposal, 'funds_requested', 0) if item.proposal else 0
                        ),
                    'submissionDate': item.created_at.isoformat() if item.created_at else None,
                    'contactPerson': proposal_data.get('contact_person', 'N/A'),
                    'contactEmail': proposal_data.get('contact_email', 'N/A'),
                    'contactPhone': proposal_data.get('contact_phone', 'N/A'),
                    
                    # Status mapping
                    'assignment_status': item.assignment_status,
                    'overall_decision': item.overall_decision,
                    
                    # Cached fields
                    'assigned_evaluators_count': item.cached_assigned_count,
                    'completed_evaluations_count': item.cached_completed_count,
                    'evaluation_marks_summary': item.cached_marks_summary,
                    'assigned_evaluators': item.cached_evaluator_data or [],
                    'completed_evaluations': [e for e in (item.cached_evaluator_data or []) if e.get('is_completed')],
                    
                    # Document URLs - FIXED MEDIA PATH
                    'applicationDocument': self._get_document_url(item.proposal),
                    'administrativeScreeningDocument': None,
                    'technicalScreeningDocument': None,
                    'first_milestone_id': None,
                }
                
                serialized_data.append(item_data)
                
            except Exception as e:
                logger.error(f"Error serializing item {getattr(item, 'id', 'unknown')}: {e}")
                # Add minimal error item
                serialized_data.append({
                    'id': getattr(item, 'id', 0),
                    'proposal_id': f'Error-{getattr(item, "id", 0)}',
                    'call': 'Error',
                    'orgType': 'Error',
                    'orgName': 'Error loading data',
                    'subject': 'Error loading data',
                    'description': 'Error loading data',
                    'fundsRequested': 0,
                    'submissionDate': None,
                    'contactPerson': 'N/A',
                    'contactEmail': 'N/A',
                    'contactPhone': 'N/A',
                    'assignment_status': 'pending',
                    'overall_decision': 'pending',
                    'assigned_evaluators_count': 0,
                    'completed_evaluations_count': 0,
                    'evaluation_marks_summary': None,
                    'assigned_evaluators': [],
                    'completed_evaluations': [],
                    'applicationDocument': None,
                    'administrativeScreeningDocument': None,
                    'technicalScreeningDocument': None,
                    'first_milestone_id': None,
                })

        return serialized_data

    @action(detail=False, methods=['get'], url_path='debug-formsubmission-fields')
    def debug_formsubmission_fields(self, request):
        """Debug FormSubmission model structure and field values"""
        if not self._is_admin_user(request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Get first few evaluation rounds with proposals
            eval_rounds = TechnicalEvaluationRound.objects.filter(
                proposal__isnull=False
            ).select_related('proposal', 'proposal__applicant', 'proposal__service')[:3]
            
            if not eval_rounds.exists():
                return Response({'error': 'No evaluation rounds with proposals found!'})
            
            # Get FormSubmission model fields
            first_proposal = eval_rounds.first().proposal
            model_fields = []
            for field in first_proposal._meta.fields:
                field_info = {
                    'name': field.name,
                    'type': field.__class__.__name__,
                    'null': field.null,
                    'blank': field.blank,
                }
                model_fields.append(field_info)
            
            # Show actual field values for first few proposals
            debug_data = []
            for i, eval_round in enumerate(eval_rounds, 1):
                proposal = eval_round.proposal
                proposal_id = getattr(proposal, 'proposal_id', f'ID-{eval_round.id}')
                
                # Show key field values
                key_fields = {
                    'proposal_id': getattr(proposal, 'proposal_id', None),
                    'subject': getattr(proposal, 'subject', None),
                    'description': getattr(proposal, 'description', None),
                    'org_type': getattr(proposal, 'org_type', None),
                    'org_address_line1': getattr(proposal, 'org_address_line1', None),
                    'contact_name': getattr(proposal, 'contact_name', None),
                    'contact_email': getattr(proposal, 'contact_email', None),
                    'org_mobile': getattr(proposal, 'org_mobile', None),
                    'current_trl': getattr(proposal, 'current_trl', None),
                    'grants_from_ttdf': getattr(proposal, 'grants_from_ttdf', None),
                }
                
                # Add User fields
                user_fields = {}
                if proposal.applicant:
                    user_fields = {
                        'User.full_name': getattr(proposal.applicant, 'full_name', None),
                        'User.email': getattr(proposal.applicant, 'email', None),
                        'User.organization': getattr(proposal.applicant, 'organization', None),
                    }
                
                # Add Service name
                service_name = None
                if proposal.service:
                    service_name = getattr(proposal.service, 'name', None)
                
                debug_info = {
                    'proposal_id': proposal_id,
                    'formsubmission_fields': key_fields,
                    'user_fields': user_fields,
                    'service_name': service_name,
                }
                debug_data.append(debug_info)
            
            return Response({
                'success': True,
                'model_fields_count': len(model_fields),
                'model_fields': model_fields[:20],  # First 20 fields
                'sample_data': debug_data,
                'field_mapping': {
                    'subject': 'FormSubmission.subject',
                    'org_type': 'FormSubmission.org_type',
                    'description': 'FormSubmission.description',
                    'org_name': 'User.organization OR FormSubmission.org_address_line1',
                    'contact_person': 'User.full_name OR FormSubmission.contact_name',
                    'contact_email': 'User.email OR FormSubmission.contact_email',
                    'contact_phone': 'FormSubmission.org_mobile',
                    'current_trl': 'FormSubmission.current_trl',
                    'call_name': 'Service.name',
                }
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='assign-evaluators')
    def assign_evaluators(self, request):
        """Assign evaluators with automatic cache updates"""
        if not self._is_admin_user(request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        evaluation_round_id = request.data.get('evaluation_round_id')
        evaluator_ids = request.data.get('evaluator_ids', [])
        
        if not evaluation_round_id or not evaluator_ids:
            return Response({'error': 'evaluation_round_id and evaluator_ids are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            start_time = time.time()
            
            evaluation_round = get_object_or_404(TechnicalEvaluationRound, id=evaluation_round_id)
            
            # Clear existing assignments
            evaluation_round.evaluator_assignments.all().delete()
            
            # Bulk create new assignments
            assignments = []
            evaluators = User.objects.filter(id__in=evaluator_ids).only('id', 'full_name', 'email')
            
            for evaluator in evaluators:
                assignments.append(EvaluatorAssignment(
                    evaluation_round=evaluation_round,
                    evaluator=evaluator
                ))
            
            EvaluatorAssignment.objects.bulk_create(assignments)
            
            # Update status
            evaluation_round.assignment_status = 'assigned'
            evaluation_round.assigned_by = request.user
            evaluation_round.save()
            
            for evaluator in evaluators:
                send_notification(
                    recipient=evaluator,
                    message=f'You have been assigned to evaluate proposal {evaluation_round.proposal.proposal_id}.',
                    notification_type="evaluator_assignment"
                )

            # The signals will automatically update cached values
            
            elapsed = time.time() - start_time
            logger.info(f"Assigned {len(assignments)} evaluators in {elapsed:.3f} seconds")
            
            return Response({
                'success': True,
                'message': f'{len(assignments)} evaluators assigned successfully',
                'assignment_count': len(assignments)
            })
            
        except Exception as e:
            logger.error(f"Assignment failed: {e}")
            return Response({'error': f'Assignment failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='available-evaluators')
    def available_evaluators(self, request):
        """Get available evaluators list (optimized)"""
        if not self._is_admin_user(request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Optimized query with minimal fields and safe filtering
            base_filter = Q()
            
            # Try different ways to identify evaluators
            if hasattr(User, 'is_evaluator'):
                base_filter |= Q(is_evaluator=True)
            
            # Check for roles if available
            try:
                if hasattr(User, 'roles'):
                    base_filter |= Q(roles__name__in=['Evaluator', 'Technical_Evaluator'])
            except Exception:
                pass
            
            # Fallback: get all active users if no specific evaluator identification
            if not base_filter.children:
                base_filter = Q(is_active=True)
            
            evaluators = User.objects.filter(base_filter).distinct().only(
                'id', 'full_name', 'email', 'mobile'
            )
            
            # Fast serialization with safe field access
            evaluators_data = []
            for evaluator in evaluators:
                try:
                    # Use full_name directly from User model
                    full_name = getattr(evaluator, 'full_name', '').strip()
                    if not full_name:
                        full_name = getattr(evaluator, 'email', 'Unknown')
                    
                    evaluators_data.append({
                        'id': evaluator.id,
                        'name': full_name,
                        'email': getattr(evaluator, 'email', ''),
                        'mobile': getattr(evaluator, 'mobile', 'N/A'),
                        'specialization': 'Technical Expert',  # Simplified for speed
                        'profile': {
                            'specialization': 'Technical Expert'
                        }
                    })
                except Exception as e:
                    logger.warning(f"Error serializing evaluator {evaluator.id}: {e}")
            
            return Response({'success': True, 'data': evaluators_data})
            
        except Exception as e:
            logger.error(f"Failed to fetch evaluators: {e}")
            return Response({'error': f'Failed to fetch evaluators: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='manual-shortlist')
    def manual_shortlist(self, request):
        """Manual shortlisting with automatic cache updates"""
        if not self._is_admin_user(request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        evaluation_round_id = request.data.get('evaluation_round_id')
        decision = request.data.get('decision')
        
        if not evaluation_round_id or not decision:
            return Response({'error': 'evaluation_round_id and decision are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if decision not in ['recommended', 'not_recommended']:
            return Response({'error': 'decision must be either "recommended" or "not_recommended"'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Fast lookup
            try:
                evaluation_round_id_int = int(evaluation_round_id)
                evaluation_round = TechnicalEvaluationRound.objects.get(id=evaluation_round_id_int)
            except (ValueError, TechnicalEvaluationRound.DoesNotExist):
                evaluation_round = TechnicalEvaluationRound.objects.get(proposal__proposal_id=evaluation_round_id)
            
            # Use cached values for completion check (FAST!)
            if evaluation_round.cached_assigned_count == 0 or evaluation_round.cached_completed_count < evaluation_round.cached_assigned_count:
                return Response({'error': 'Cannot shortlist until all evaluations are completed'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update decision
            evaluation_round.overall_decision = decision
            evaluation_round.assignment_status = 'completed'
            evaluation_round.completed_at = timezone.now()
            evaluation_round.save()
            
            # Create presentation record if recommended
            presentation_created = False
            assigned_evaluator = None
            
            if decision == 'recommended':
                try:
                    from presentation.models import Presentation
                    if not Presentation.objects.filter(proposal=evaluation_round.proposal).exists():
                        # Use cached evaluator data to find first evaluator
                        if evaluation_round.cached_evaluator_data:
                            completed_evaluators = [e for e in evaluation_round.cached_evaluator_data if e.get('is_completed')]
                            if completed_evaluators:
                                first_evaluator_id = completed_evaluators[0].get('id')
                                try:
                                    evaluator = User.objects.get(id=first_evaluator_id)
                                    
                                    Presentation.objects.create(
                                        proposal=evaluation_round.proposal,
                                        applicant=evaluation_round.proposal.applicant,
                                        evaluator=evaluator,
                                        final_decision='pending'
                                    )
                                    presentation_created = True
                                    assigned_evaluator = getattr(evaluator, 'full_name', str(evaluator))
                                except User.DoesNotExist:
                                    logger.warning(f"Evaluator {first_evaluator_id} not found")
                except Exception as e:
                    logger.warning(f"Failed to create presentation: {e}")
            
            response_data = {
                'success': True,
                'message': f'Proposal {decision.replace("_", " ")} successfully',
                'decision': decision,
                'evaluation_round_id': evaluation_round.id,
                'proposal_id': self._safe_get_attribute(evaluation_round, 'proposal.proposal_id')
            }
            
            if presentation_created:
                response_data['presentation_created'] = True
                response_data['assigned_evaluator'] = assigned_evaluator
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Shortlisting failed: {e}")
            return Response({'error': f'Shortlisting failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='debug-user')
    def debug_user(self, request):
        """Debug user permissions"""
        user = request.user
        user_roles = []
        try:
            if hasattr(user, 'roles'):
                user_roles = [role.name for role in user.roles.all()]
        except Exception:
            pass
            
        return Response({
            'user_id': user.id,
            'username': getattr(user, 'email', getattr(user, 'username', 'Unknown')),
            'is_authenticated': user.is_authenticated,
            'is_staff': getattr(user, 'is_staff', False),
            'is_superuser': getattr(user, 'is_superuser', False),
            'is_admin': getattr(user, 'is_admin', False),
            'is_evaluator': getattr(user, 'is_evaluator', False),
            'roles': user_roles,
            'user_permissions': [perm.codename for perm in user.user_permissions.all()],
            'groups': [group.name for group in user.groups.all()],
            'is_admin_check': self._is_admin_user(user),
            'is_evaluator_check': self._is_evaluator_user(user),
        })

    @action(detail=False, methods=['get'])
    def api_health_check(self, request):
        """API health check with performance metrics"""
        start_time = time.time()
        
        # Test cached fields performance
        try:
            count = TechnicalEvaluationRound.objects.count()
            
            # Test a small query using cached fields
            sample_data = TechnicalEvaluationRound.objects.only(
                'id', 'cached_assigned_count', 'cached_completed_count', 'cached_average_percentage'
            )[:5]
            
            sample_results = list(sample_data)
            
            elapsed = time.time() - start_time
            
            return Response({
                "total_rows": count,
                "sample_size": len(sample_results),
                "duration_sec": round(elapsed, 3),
                "cached_fields_available": bool(sample_results and hasattr(sample_results[0], 'cached_assigned_count')),
                "status": "healthy" if elapsed < 1.0 else "slow"
            })
            
        except Exception as e:
            return Response({
                "error": str(e),
                "duration_sec": round(time.time() - start_time, 3),
                "status": "unhealthy"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EvaluatorAssignmentViewSet(viewsets.ModelViewSet):
    """Optimized EvaluatorAssignment ViewSet using cached fields"""
    permission_classes = [IsAuthenticated]
    serializer_class = LightningFastEvaluatorAssignmentSerializer

    def _is_admin_user(self, user):
        return (
            getattr(user, 'is_staff', False) or 
            getattr(user, 'is_superuser', False) or 
            getattr(user, 'is_admin', False)
        )

    def get_queryset(self):
        user = self.request.user
        base_qs = EvaluatorAssignment.objects.select_related('evaluator', 'evaluation_round').only(
        'id', 'is_completed', 'overall_comments', 'expected_trl', 'conflict_of_interest',
        'cached_raw_marks', 'cached_max_marks', 'cached_percentage_score', 'cached_criteria_count',
        'assigned_at', 'completed_at',
        'evaluator__id', 'evaluator__full_name', 'evaluator__email',
        'evaluation_round__id', 'evaluation_round__assignment_status',
        'evaluator_id', 'evaluation_round_id'
    )
    
        if self._is_admin_user(user):
           return base_qs.all()
        return base_qs.filter(evaluator=user)

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='submit-evaluation')
    def submit_evaluation(self, request, pk=None):
        """Submit evaluation with automatic cache updates"""
        assignment = self.get_object()
        
        # Permission check
        if not (self._is_admin_user(request.user) or assignment.evaluator == request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if assignment.is_completed:
            return Response({'error': 'Evaluation already completed'}, status=status.HTTP_400_BAD_REQUEST)
        
        criteria_evaluations = request.data.get('criteria_evaluations', [])
        overall_comments = request.data.get('overall_comments', '')
        expected_trl = request.data.get('expected_trl')
        conflict_of_interest = request.data.get('conflict_of_interest', False)
        conflict_remarks = request.data.get('conflict_remarks', '')
        
        if not criteria_evaluations:
            return Response({'error': 'criteria_evaluations is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            start_time = time.time()
            
            # Clear existing evaluations
            assignment.criteria_evaluations.all().delete()
            
            # Bulk create criteria evaluations
            criteria_to_create = []
            for criteria_eval in criteria_evaluations:
                criteria_id = criteria_eval.get('criteria_id')
                marks = float(criteria_eval.get('marks', 0))
                remarks = criteria_eval.get('remarks', '')
                
                try:
                    from app_eval.models import EvaluationItem
                    evaluation_criteria = EvaluationItem.objects.get(
                        id=criteria_id, 
                        status='Active', 
                        type='criteria'
                    )
                    
                    max_marks = float(evaluation_criteria.total_marks)
                    if marks < 0 or marks > max_marks:
                        return Response({
                            'error': f'Marks for criteria "{evaluation_criteria.name}" must be between 0 and {max_marks}'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    criteria_to_create.append(CriteriaEvaluation(
                        evaluator_assignment=assignment,
                        evaluation_criteria=evaluation_criteria,
                        marks_given=marks,
                        remarks=remarks
                    ))
                    
                except Exception as e:
                    return Response({
                        'error': f'Error with criteria {criteria_id}: {str(e)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Bulk create
            CriteriaEvaluation.objects.bulk_create(criteria_to_create)
            
            # Update assignment
            assignment.overall_comments = overall_comments
            if expected_trl:
                assignment.expected_trl = int(expected_trl)
            assignment.conflict_of_interest = conflict_of_interest
            assignment.conflict_remarks = conflict_remarks
            assignment.is_completed = True
            assignment.completed_at = timezone.now()
            assignment.save()


            # Notify Applicant
            if applicant:
                send_notification(
                    recipient=applicant,
                    message=f'Your proposal ({getattr(proposal, "proposal_id", "N/A")}) has been evaluated by {request.user.get_full_name()}.',
                    notification_type="proposal_evaluated"
                )

            # Notify Admins (all admins; customize as needed)
            
            admin_and_user_role_users = User.objects.filter(
            roles__name__in=["Admin"]
            ).exclude(id=applicant.id).distinct()

            for user in admin_and_user_role_users:
                send_notification(
                    recipient=user,
                    message=f'Proposal ({getattr(proposal, "proposal_id", "N/A")}) has been evaluated by {request.user.get_full_name()}.',
                    notification_type="proposal_evaluated_role"
                )
            
            # Signals will automatically update cached values
            
            elapsed = time.time() - start_time
            logger.info(f"Evaluation submitted in {elapsed:.3f} seconds")
            
            return Response({
                'success': True,
                'message': 'Evaluation submitted successfully',
                'criteria_count': len(criteria_evaluations),
                'expected_trl': expected_trl,
                'conflict_of_interest': conflict_of_interest,
                'assignment_id': assignment.id,
                'cached_percentage': getattr(assignment, 'cached_percentage_score', None)
            })
            
        except Exception as e:
            logger.error(f"Evaluation submission failed: {e}")
            return Response({'error': f'Submission failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EvaluationCriteriaViewSet(viewsets.ReadOnlyModelViewSet):
    """Fast criteria fetching from app_eval"""
    permission_classes = [IsAuthenticated]
    serializer_class = FastAppEvalCriteriaSerializer
    
    def list(self, request):
        try:
            from app_eval.models import EvaluationItem
            criteria = EvaluationItem.objects.filter(
                status='Active',
                type='criteria'
            ).only('id', 'name', 'description', 'total_marks')
            
            # Fast serialization
            criteria_data = [
                {
                    'id': item.id,
                    'name': item.name,
                    'description': getattr(item, 'description', ''),
                    'total_marks': item.total_marks,
                    'weightage': getattr(item, 'weightage', 0),
                    'status': 'Active',
                    'type': 'criteria'
                }
                for item in criteria
            ]
            
            return Response({'success': True, 'data': criteria_data})
            
        except Exception as e:
            logger.error(f"Failed to fetch criteria: {e}")
            return Response({'error': f'Failed to fetch criteria: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CriteriaEvaluationViewSet(viewsets.ModelViewSet):
    """Optimized Criteria Evaluation ViewSet"""
    permission_classes = [IsAuthenticated]
    serializer_class = LightningFastCriteriaEvaluationSerializer

    def _is_admin_user(self, user):
        return (
            getattr(user, 'is_staff', False) or 
            getattr(user, 'is_superuser', False) or 
            getattr(user, 'is_admin', False)
        )

    def get_queryset(self):
        user = self.request.user
        base_qs = CriteriaEvaluation.objects.select_related(
            'evaluator_assignment__evaluator',
            'evaluation_criteria'
        ).only(
            'id', 'marks_given', 'remarks', 'cached_percentage', 'cached_weighted_score', 'evaluated_at',
            'evaluator_assignment__evaluator__full_name',
            'evaluation_criteria__name', 'evaluation_criteria__total_marks'
        )
        
        if self._is_admin_user(user):
            return base_qs.all()
        return base_qs.filter(evaluator_assignment__evaluator=user)

    def list(self, request):
        try:
            queryset = self.get_queryset()[:100]  # Limit for performance
            
            # Fast serialization using cached fields
            data = []
            for item in queryset:
                try:
                    evaluator_name = getattr(item.evaluator_assignment.evaluator, 'full_name', 'Unknown')
                    
                    data.append({
                        'id': item.id,
                        'evaluator_name': evaluator_name,
                        'criteria_name': getattr(item.evaluation_criteria, 'name', 'Unknown'),
                        'marks_given': float(item.marks_given),
                        'max_marks': float(getattr(item.evaluation_criteria, 'total_marks', 0)),
                        'percentage': getattr(item, 'cached_percentage', 0) or 0,  # Use cached value!
                        'weighted_score': getattr(item, 'cached_weighted_score', 0) or 0,  # Use cached value!
                        'remarks': item.remarks,
                        'evaluated_at': item.evaluated_at.isoformat() if item.evaluated_at else None
                    })
                except Exception as e:
                    logger.warning(f"Error serializing criteria evaluation {item.id}: {e}")
            
            return Response({
                'success': True,
                'data': data,
                'count': len(data)
            })
            
        except Exception as e:
            logger.error(f"Failed to fetch criteria evaluations: {e}")
            return Response({'error': f'Failed to fetch criteria evaluations: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='by-assignment/(?P<assignment_id>[^/.]+)')
    def by_assignment(self, request, assignment_id=None):
        """Get criteria evaluations for specific assignment using cached data"""
        try:
            user = request.user
            
            # Get assignment with permission check
            if self._is_admin_user(user):
                assignment = get_object_or_404(EvaluatorAssignment, id=assignment_id)
            else:
                assignment = get_object_or_404(EvaluatorAssignment, id=assignment_id, evaluator=user)
            
            # Use cached criteria data if available
            if hasattr(assignment, 'cached_criteria_data') and assignment.cached_criteria_data:
                criteria_data = assignment.cached_criteria_data
            else:
                # Fallback to database query
                criteria_evaluations = self.get_queryset().filter(evaluator_assignment=assignment)
                criteria_data = []
                for item in criteria_evaluations:
                    try:
                        criteria_data.append({
                            'id': item.id,
                            'criteria_name': getattr(item.evaluation_criteria, 'name', 'Unknown'),
                            'marks_given': float(item.marks_given),
                            'max_marks': float(getattr(item.evaluation_criteria, 'total_marks', 0)),
                            'percentage': getattr(item, 'cached_percentage', 0) or 0,
                            'remarks': item.remarks,
                        })
                    except Exception as e:
                        logger.warning(f"Error processing criteria evaluation {item.id}: {e}")
            
            evaluator_name = 'Unknown'
            try:
                evaluator_name = getattr(assignment.evaluator, 'full_name', str(assignment.evaluator))
            except Exception:
                pass
            
            return Response({
                'success': True,
                'data': criteria_data,
                'assignment_id': assignment_id,
                'evaluator': evaluator_name,
                'is_completed': getattr(assignment, 'is_completed', False),
                'cached_percentage_score': getattr(assignment, 'cached_percentage_score', None),
                'cached_raw_marks': getattr(assignment, 'cached_raw_marks', None),
                'cached_max_marks': getattr(assignment, 'cached_max_marks', None)
            })
            
        except Exception as e:
            logger.error(f"Failed to fetch criteria evaluations: {e}")
            return Response({'error': f'Failed to fetch criteria evaluations: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Additional ViewSets for evaluator interface
class EvaluatorDashboardViewSet(viewsets.ReadOnlyModelViewSet):
    """Evaluator dashboard with cached data"""
    permission_classes = [IsAuthenticated]
    serializer_class = LightningFastEvaluatorAssignmentSerializer
    
    @action(detail=False, methods=['get'], url_path='my-assignments')
    def my_assignments(self, request):
        """Get evaluator's assignments using cached data"""
        try:
            user = request.user
            
            # Get assignments for this evaluator
            assignments = EvaluatorAssignment.objects.filter(
                evaluator=user
            ).select_related(
                'evaluation_round__proposal',
                'evaluation_round__proposal__service'
            ).only(
                'id', 'is_completed', 'assigned_at', 'completed_at',
                'cached_percentage_score', 'cached_raw_marks', 'cached_max_marks',
                'evaluation_round_id', 'evaluation_round__proposal__proposal_id',
                'evaluation_round__proposal__subject', 'evaluation_round__proposal__service__name'
            ).order_by('-assigned_at')
            
            # Fast serialization
            assignments_data = []
            for assignment in assignments:
                try:
                    proposal = assignment.evaluation_round.proposal
                    assignments_data.append({
                        'id': assignment.id,
                        'evaluation_round_id': assignment.evaluation_round_id,
                        'proposal_id': getattr(proposal, 'proposal_id', 'N/A'),
                        'subject': getattr(proposal, 'subject', 'N/A'),
                        'service_name': getattr(proposal.service, 'name', 'N/A') if proposal.service else 'N/A',
                        'is_completed': assignment.is_completed,
                        'assigned_at': assignment.assigned_at.isoformat() if assignment.assigned_at else None,
                        'completed_at': assignment.completed_at.isoformat() if assignment.completed_at else None,
                        'cached_percentage_score': assignment.cached_percentage_score,
                        'cached_raw_marks': assignment.cached_raw_marks,
                        'cached_max_marks': assignment.cached_max_marks,
                        'status': 'completed' if assignment.is_completed else 'pending'
                    })
                except Exception as e:
                    logger.warning(f"Error serializing assignment {assignment.id}: {e}")
            
            return Response({
                'success': True,
                'data': assignments_data,
                'total_assignments': len(assignments_data),
                'completed_assignments': sum(1 for a in assignments_data if a.get('is_completed')),
                'pending_assignments': sum(1 for a in assignments_data if not a.get('is_completed'))
            })
            
        except Exception as e:
            logger.error(f"Failed to fetch evaluator assignments: {e}")
            return Response({'error': f'Failed to fetch assignments: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='assignment-details/(?P<assignment_id>[^/.]+)')
    def assignment_details(self, request, assignment_id=None):
        """Get detailed assignment info for evaluator"""
        try:
            user = request.user
            
            # Get assignment with all related data
            assignment = get_object_or_404(
                EvaluatorAssignment.objects.select_related(
                    'evaluation_round__proposal',
                    'evaluation_round__proposal__service',
                    'evaluation_round__proposal__applicant'
                ),
                id=assignment_id,
                evaluator=user
            )
            
            proposal = assignment.evaluation_round.proposal
            
            # Build detailed response
            assignment_data = {
                'id': assignment.id,
                'evaluation_round_id': assignment.evaluation_round.id,
                'is_completed': assignment.is_completed,
                'overall_comments': assignment.overall_comments,
                'expected_trl': assignment.expected_trl,
                'conflict_of_interest': assignment.conflict_of_interest,
                'conflict_remarks': assignment.conflict_remarks,
                'assigned_at': assignment.assigned_at.isoformat() if assignment.assigned_at else None,
                'completed_at': assignment.completed_at.isoformat() if assignment.completed_at else None,
                
                # Cached scores
                'cached_percentage_score': assignment.cached_percentage_score,
                'cached_raw_marks': assignment.cached_raw_marks,
                'cached_max_marks': assignment.cached_max_marks,
                'cached_criteria_count': assignment.cached_criteria_count,
                
                # Proposal details from FormSubmission
                'proposal': {
                    'id': proposal.id,
                    'proposal_id': getattr(proposal, 'proposal_id', 'N/A'),
                    'subject': getattr(proposal, 'subject', 'N/A'),
                    'description': getattr(proposal, 'description', 'N/A'),
                    'org_type': getattr(proposal, 'org_type', 'N/A'),
                    'service_name': getattr(proposal.service, 'name', 'N/A') if proposal.service else 'N/A',
                    'current_trl': getattr(proposal, 'current_trl', None),
                    'abstract': getattr(proposal, 'abstract', 'N/A'),
                    'technical_feasibility': getattr(proposal, 'technical_feasibility', 'N/A'),
                    'potential_impact': getattr(proposal, 'potential_impact', 'N/A'),
                    'commercialization_strategy': getattr(proposal, 'commercialization_strategy', 'N/A'),
                    
                    # Contact info
                    'contact_name': getattr(proposal, 'contact_name', 'N/A'),
                    'contact_email': getattr(proposal, 'contact_email', 'N/A'),
                    'org_mobile': getattr(proposal, 'org_mobile', 'N/A'),
                },
                
                # Document URLs
                'documents': {
                    'application_document': proposal.applicationDocument.url if proposal.applicationDocument else None,
                }
            }
            
            return Response({
                'success': True,
                'data': assignment_data
            })
            
        except Exception as e:
            logger.error(f"Failed to fetch assignment details: {e}")
            return Response({'error': f'Failed to fetch assignment details: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Performance monitoring viewset
class PerformanceMonitoringViewSet(viewsets.ReadOnlyModelViewSet):
    """Monitor system performance"""
    permission_classes = [IsAuthenticated]
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class EmptySerializer(serializers.Serializer):
            pass
        
        return EmptySerializer
    
    @action(detail=False, methods=['get'], url_path='cache-status')
    def cache_status(self, request):
        """Check cache status and performance"""
        if not (getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False)):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            start_time = time.time()
            
            # Count total records
            total_rounds = TechnicalEvaluationRound.objects.count()
            total_assignments = EvaluatorAssignment.objects.count()
            total_criteria = CriteriaEvaluation.objects.count()
            
            # Check cache completeness
            rounds_with_cache = TechnicalEvaluationRound.objects.exclude(
                cached_assigned_count__isnull=True
            ).count()
            
            assignments_with_cache = EvaluatorAssignment.objects.exclude(
                cached_percentage_score__isnull=True,
                is_completed=True
            ).count()
            
            completed_assignments = EvaluatorAssignment.objects.filter(is_completed=True).count()
            
            criteria_with_cache = CriteriaEvaluation.objects.exclude(
                cached_percentage__isnull=True
            ).count()
            
            # Test query performance
            query_start = time.time()
            sample_rounds = list(TechnicalEvaluationRound.objects.only(
                'id', 'cached_assigned_count', 'cached_completed_count'
            )[:10])
            query_elapsed = time.time() - query_start
            
            elapsed = time.time() - start_time
            
            cache_completeness = {
                'rounds': {
                    'total': total_rounds,
                    'cached': rounds_with_cache,
                    'percentage': round((rounds_with_cache / total_rounds * 100), 2) if total_rounds > 0 else 0
                },
                'assignments': {
                    'total': completed_assignments,
                    'cached': assignments_with_cache,
                    'percentage': round((assignments_with_cache / completed_assignments * 100), 2) if completed_assignments > 0 else 0
                },
                'criteria': {
                    'total': total_criteria,
                    'cached': criteria_with_cache,
                    'percentage': round((criteria_with_cache / total_criteria * 100), 2) if total_criteria > 0 else 0
                }
            }
            
            return Response({
                'success': True,
                'cache_completeness': cache_completeness,
                'performance': {
                    'total_analysis_time': round(elapsed, 3),
                    'query_time_10_records': round(query_elapsed, 3),
                    'sample_size': len(sample_rounds)
                },
                'recommendations': self._get_cache_recommendations(cache_completeness)
            })
            
        except Exception as e:
            logger.error(f"Cache status check failed: {e}")
            return Response({'error': f'Cache status check failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_cache_recommendations(self, cache_completeness):
        """Get cache optimization recommendations"""
        recommendations = []
        
        if cache_completeness['rounds']['percentage'] < 90:
            recommendations.append("Run: python3 manage.py fix_formsubmission_cache --force")
        
        if cache_completeness['assignments']['percentage'] < 90:
            recommendations.append("Run: python3 manage.py fix_evaluator_cache --force")
        
        if cache_completeness['criteria']['percentage'] < 90:
            recommendations.append("Run: python3 manage.py update_cached_values_safe --model=criteria")
        
        if not recommendations:
            recommendations.append("Cache is in good condition!")
        
        return recommendations
    



    # API 



class EvaluatorListView(APIView):
    def get(self, request):
        try:
            users = User.objects.filter(is_active=True)  # Add more filters if needed

            # You may want to filter for only evaluators if you have a flag/group

            data = []
            for user in users:
                data.append({
                    'id': user.id,
                    'name': user.get_full_name() if hasattr(user, 'get_full_name') else str(user),
                    'email': user.email,
                    'expertise': getattr(user, 'expertise', ''),  # Or from profile if needed
                })

            return Response({
                "success": True,
                "message": "Evaluators fetched successfully",
                "data": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "success": False,
                "message": f"An error occurred: {str(e)}",
                "data": []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



