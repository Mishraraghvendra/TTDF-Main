# presentation/views.py
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import Presentation
from .serializers import (
    PresentationSerializer, 
    AdminPresentationListSerializer,
    EvaluatorPresentationSerializer,
    PersonalInterviewSerializer,UltraFastFormSubmissionSerializer
)
from dynamic_form.models import FormSubmission
from django.db.models import Avg, Count, Prefetch
import logging
logger = logging.getLogger(__name__)
import time
# from rest_framework_orjson.renderers import ORJSONRenderer
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator


User = get_user_model()

# @method_decorator(cache_page(60 * 60 * 2), name='dispatch')
class PresentationViewSet(viewsets.ModelViewSet):
    class PresentationViewSet(viewsets.ModelViewSet):
        queryset = Presentation.objects.select_related(
            'proposal__service__passing_requirement',  # for access logic
            'applicant', 'evaluator', 'admin'
        )
        serializer_class = PresentationSerializer
        permission_classes = [IsAuthenticated]

    def _is_admin_user(self, user):
        """Check if user has admin privileges"""
        return (
            user.is_staff or 
            user.is_superuser or 
            getattr(user, 'is_admin', False) or
            user.has_role('Admin') or 
            user.has_role('SuperAdmin') or
            user.has_role('Technical_Admin')
        )

    def _is_evaluator_user(self, user):
        """Check if user is an evaluator"""
        return (
            getattr(user, 'is_evaluator', False) or
            user.has_role('Evaluator') or
            user.has_role('Technical_Evaluator')
        )

    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        
        if self._is_admin_user(user):
            return Presentation.objects.select_related(
                'proposal', 'applicant', 'evaluator', 'admin'
            ).all()
        elif self._is_evaluator_user(user):
            return Presentation.objects.select_related(
                'proposal', 'applicant', 'evaluator', 'admin'
            ).filter(evaluator=user)
        else:
            # Applicants see only their own presentations
            return Presentation.objects.select_related(
                'proposal', 'applicant', 'evaluator', 'admin'
            ).filter(applicant=user)

    def get_serializer_class(self):
        """Return appropriate serializer based on action and user role"""
        if self.action == 'admin_list':
            return AdminPresentationListSerializer
        elif self.action in ['my_evaluations', 'submit_evaluation']:
            return EvaluatorPresentationSerializer
        return PresentationSerializer

    @action(detail=False, methods=['get'], url_path='admin-list')
    def admin_list(self, request):
        """Get all presentations for admin management"""
        if not self._is_admin_user(request.user):
            return Response(
                {'error': 'Permission denied', 'detail': 'Admin privileges required'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            queryset = Presentation.objects.select_related(
                'proposal', 'applicant', 'evaluator', 'admin'
            ).prefetch_related('proposal__milestones').order_by('-created_at')
            
            serializer = AdminPresentationListSerializer(queryset, many=True)
            return Response({
                'success': True,
                'data': serializer.data,
                'count': queryset.count()
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch presentations: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='my-evaluations')
    def my_evaluations(self, request):
        """Get presentations assigned to current evaluator"""
        if not self._is_evaluator_user(request.user):
            return Response(
                {'error': 'Permission denied', 'detail': 'Evaluator privileges required'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            queryset = Presentation.objects.select_related(
                'proposal', 'applicant'
            ).filter(evaluator=request.user).order_by('-created_at')
            
            serializer = EvaluatorPresentationSerializer(queryset, many=True)
            return Response({
                'success': True,
                'data': serializer.data,
                'count': queryset.count()
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch evaluations: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='assign-materials')
    def assign_materials(self, request, pk=None):
        """Admin assigns video, document, and presentation date"""
        print("assign_materials called with data:", request.data)
        print("FILES:", request.FILES)
        if not self._is_admin_user(request.user):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        presentation = self.get_object()
        video_link = request.data.get('video_link')

        video_file = request.FILES.get('video')
        document_file = request.FILES.get('document')
        presentation_date = request.data.get('presentation_date')
        
        if not any([video_file, document_file, presentation_date]):
            return Response(
                {'error': 'At least one material must be provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validate presentation_date format if provided
            if presentation_date:
                from django.utils.dateparse import parse_datetime
                parsed_date = parse_datetime(presentation_date)
                if not parsed_date:
                    return Response(
                        {'error': 'Invalid presentation_date format. Use ISO format.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Assign materials
            presentation.assign_materials(
                video_file=video_file,
                video_link=video_link,
                document_file=document_file,
                presentation_date=parsed_date if presentation_date else None,
                admin_user=request.user
            )
            
            return Response({
                'success': True,
                'message': 'Materials assigned successfully',
                'document_uploaded': presentation.document_uploaded,
                'final_decision': presentation.final_decision
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to assign materials: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='submit-evaluation')
    def submit_evaluation(self, request, pk=None):
        """Evaluator submits marks and remarks"""
        presentation = self.get_object()
        
        # Check if user is the assigned evaluator
        if presentation.evaluator != request.user:
            return Response(
                {'error': 'Permission denied', 'detail': 'You are not assigned to evaluate this presentation'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if presentation is ready for evaluation
        if not presentation.is_ready_for_evaluation:
            return Response(
                {'error': 'Presentation is not ready for evaluation'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already evaluated
        if presentation.is_evaluation_completed:
            return Response(
                {'error': 'Evaluation already completed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        marks = request.data.get('evaluator_marks')
        remarks = request.data.get('evaluator_remarks', '')
        
        if marks is None:
            return Response(
                {'error': 'evaluator_marks is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            marks = float(marks)
            
            # Simple validation - just check for non-negative number
            if marks < 0:
                return Response(
                    {'error': 'Marks must be a positive number'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Submit evaluation
            presentation.submit_evaluation(marks, remarks)
            
            return Response({
                'success': True,
                'message': 'Evaluation submitted successfully',
                'evaluator_marks': marks,
                'final_decision': presentation.final_decision
            })
            
        except ValueError:
            return Response(
                {'error': 'Invalid marks format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to submit evaluation: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='final-decision')
    def final_decision(self, request, pk=None):
        """Admin makes final decision on presentation"""
        if not self._is_admin_user(request.user):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        presentation = self.get_object()
        
        # Check if can make final decision
        if not presentation.can_make_final_decision:
            return Response(
                {'error': 'Cannot make final decision. Evaluation must be completed first.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        decision = request.data.get('final_decision')
        admin_remarks = request.data.get('admin_remarks', '')
        
        if decision not in ['shortlisted', 'rejected']:
            return Response(
                {'error': 'final_decision must be either "shortlisted" or "rejected"'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            presentation.update_admin_decision(
                admin_user=request.user,
                decision=decision,
                remarks=admin_remarks
            )
            
            return Response({
                'success': True,
                'message': f'Presentation {decision} successfully',
                'final_decision': decision,
                'admin_remarks': admin_remarks
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to update decision: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """
        Custom update to handle different user roles and operations
        """
        instance = self.get_object()
        data = request.data.copy()
        user = request.user

        # Role checks
        is_admin = self._is_admin_user(user)
        is_evaluator = self._is_evaluator_user(user)
        is_assigned_evaluator = (instance.evaluator == user)
        is_owner = (instance.applicant == user)

        # Admin operations
        if is_admin:
            # Admin can assign materials
            if any(key in data for key in ['video', 'document', 'presentation_date']):
                # Handle file uploads and date assignment
                if 'video' in request.FILES:
                    instance.video = request.FILES['video']
                if 'document' in request.FILES:
                    instance.document = request.FILES['document']
                if 'presentation_date' in data:
                    from django.utils.dateparse import parse_datetime
                    parsed_date = parse_datetime(data['presentation_date'])
                    if parsed_date:
                        instance.presentation_date = parsed_date
                
                # Update status and admin info
                instance.admin = user
                instance.admin_evaluated_at = timezone.now()
                instance.save()
                
            # Admin can make final decision
            if 'final_decision' in data and data['final_decision'] in ['shortlisted', 'rejected']:
                if not instance.can_make_final_decision:
                    return Response({
                        'error': 'Cannot make final decision before evaluation is completed'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                instance.update_admin_decision(
                    admin_user=user,
                    decision=data['final_decision'],
                    remarks=data.get('admin_remarks', '')
                )

        # Evaluator operations
        elif is_assigned_evaluator and is_evaluator:
            # Evaluator can only submit marks and remarks
            if 'evaluator_marks' in data or 'evaluator_remarks' in data:
                if not instance.is_ready_for_evaluation:
                    return Response({
                        'error': 'Presentation is not ready for evaluation'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if instance.is_evaluation_completed:
                    return Response({
                        'error': 'Evaluation already completed'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                marks = data.get('evaluator_marks')
                remarks = data.get('evaluator_remarks', instance.evaluator_remarks or '')
                
                if marks is not None:
                    try:
                        marks = float(marks)
                        
                        # Simple validation - just check for non-negative number
                        if marks < 0:
                            return Response({
                                'error': 'Marks must be a positive number'
                            }, status=status.HTTP_400_BAD_REQUEST)
                        
                        instance.submit_evaluation(marks, remarks)
                    except ValueError:
                        return Response({
                            'error': 'Invalid marks format'
                        }, status=status.HTTP_400_BAD_REQUEST)

        # Applicants can only view (handled by permissions in get_queryset)
        elif is_owner:
            # Restrict applicant modifications
            restricted_fields = [
                'video', 'document', 'presentation_date', 'document_uploaded',
                'evaluator', 'evaluator_marks', 'evaluator_remarks', 'evaluated_at',
                'final_decision', 'admin_remarks', 'admin', 'admin_evaluated_at'
            ]
            for field in restricted_fields:
                data.pop(field, None)
        
        else:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        # Use standard serializer for response
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data, status=status.HTTP_200_OK)




class PersonalInterviewViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UltraFastFormSubmissionSerializer
    # renderer_classes = [ORJSONRenderer]

    def get_queryset(self):
        # Annotate the DB with counts/averages for fast access in serializer
        return (
            FormSubmission.objects
            .select_related('applicant', 'service')
            .prefetch_related(
                Prefetch(
                    'presentations',
                    queryset=Presentation.objects.only(
                        'id', 'proposal_id', 'final_decision', 'cached_status', 'cached_evaluator_name',
                        'cached_marks_summary', 'cached_applicant_data',
                        'video', 'video_link', 'document', 'presentation_date', 'document_uploaded',
                        'created_at', 'updated_at', 'admin_remarks', 'admin', 'admin_evaluated_at',
                        'evaluator', 'evaluator_marks', 'evaluator_remarks', 'evaluated_at'
                    ).order_by('-created_at')
                ),
                'milestones',
                'screening_records'
            )
            .only(
                'proposal_id', 'org_type', 'subject', 'description', 'created_at', 'contact_email',
                'applicant__organization', 'service__name'
            )
            .filter(presentations__isnull=False)
            .distinct()
            .annotate(
                average_marks=Avg('presentations__evaluator_marks'),
                total_evaluators=Count('presentations__evaluator', distinct=True)
            )
        ) 
    

    def list(self, request, *args, **kwargs):
        start_total = time.perf_counter()
        start_qs = time.perf_counter()
        queryset = self.filter_queryset(self.get_queryset())
        end_qs = time.perf_counter()
        logger.warning(f"Queryset time: {end_qs - start_qs:.3f}s")

        start_ser = time.perf_counter()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
        else:
            serializer = self.get_serializer(queryset, many=True)
        # THIS is the important line:
        data = serializer.data  # <- This is where the heavy work happens!
        end_ser = time.perf_counter()
        logger.warning(f"Serializer time: {end_ser - start_ser:.3f}s")

        start_resp = time.perf_counter()
        if page is not None:
            response = self.get_paginated_response(data)
        else:
            response = Response(data)
        end_resp = time.perf_counter()
        logger.warning(f"Response time: {end_resp - start_resp:.3f}s")
        logger.warning(f"TOTAL time: {end_resp - start_total:.3f}s")
        return response




# class PersonalInterviewViewSet(viewsets.ReadOnlyModelViewSet):
#     """
#     ViewSet for personal interview listing with enhanced presentation data
#     """
#     queryset = FormSubmission.objects.all().prefetch_related(
#         'screening_records__technical_record',
#         'milestones',
#         'presentations'  # Include presentations
#     ).select_related(
#         'applicant', 'service'
#     )
#     serializer_class = PersonalInterviewSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         """Filter to only show proposals that have presentations"""
#         return super().get_queryset().filter(
#             presentations__isnull=False
#         ).distinct()

#     @action(detail=True, methods=['get'], url_path='presentation-only')
#     def presentation_only(self, request, pk=None):
#         """Get only presentation data for a specific proposal"""
#         try:
#             form_submission = self.get_object()
#             presentation = form_submission.presentations.order_by('-created_at').first()
            
#             if not presentation:
#                 return Response({
#                     'error': 'No presentation found for this proposal'
#                 }, status=status.HTTP_404_NOT_FOUND)
            
#             serializer = PresentationSerializer(presentation)
#             return Response({
#                 'success': True,
#                 'presentation': serializer.data
#             })
            
#         except Exception as e:
#             return Response(
#                 {'error': f'Failed to fetch presentation: {str(e)}'}, 
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
  

# class PersonalInterviewViewSet(viewsets.ReadOnlyModelViewSet):
#     permission_classes = [IsAuthenticated]
#     serializer_class = UltraFastFormSubmissionSerializer

#     def get_queryset(self):
#         return (
#             FormSubmission.objects
#             .select_related('applicant', 'service')
#             .prefetch_related(
#                 Prefetch(
#                     'presentations',
#                     queryset=Presentation.objects.only(
#                         'id', 'proposal_id', 'final_decision', 'cached_status', 'cached_evaluator_name',
#                         'cached_marks_summary', 'cached_applicant_data',
#                         'video', 'video_link', 'document', 'presentation_date', 'document_uploaded',
#                         'created_at', 'updated_at', 'admin_remarks', 'admin', 'admin_evaluated_at',
#                         'evaluator', 'evaluator_marks', 'evaluator_remarks', 'evaluated_at'
#                     ).order_by('-created_at')
#                 ),
#                 'milestones',
#                 'screening_records'
#             )
#             .only(
#                 'proposal_id', 'org_type', 'subject', 'description', 'created_at', 'contact_email',
#                 'applicant__organization', 'service__name'
#             )
#             .filter(presentations__isnull=False)
#             .distinct()
#         )
 
# @method_decorator(cache_page(60 * 60 * 2), name='dispatch')