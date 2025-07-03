# app_eval/views.py
from rest_framework import viewsets, status
from rest_framework.views import APIView
from django.db import IntegrityError
from rest_framework.generics import ListAPIView
from django.db.models import Prefetch, OuterRef, Subquery
from rest_framework.response import Response
from dynamic_form.models import FormSubmission
from screening.models import ScreeningRecord, TechnicalScreeningRecord
from rest_framework.decorators import action
from .models import (
    EvaluationItem, CriteriaType, Evaluator, 
    EvaluationAssignment, CriteriaEvaluation, 
    QuestionEvaluation, EvaluationCutoff,PassingRequirement
)
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import (
    EvaluationItemSerializer, GeneralPoolItemSerializer,
    CriteriaTypeSerializer, EvaluatorSerializer,
    EvaluationAssignmentSerializer, CriteriaEvaluationSerializer,
    QuestionEvaluationSerializer, EvaluationCutoffSerializer,
    TechnicalEvaluationSerializer,PassingRequirementSerializer,EvaluatorEmailSerializer
)


from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import PassingRequirement
from .serializers import PassingRequirementSerializer
from rest_framework.exceptions import ValidationError
from .models import PassingRequirement
from .serializers import PassingRequirementSerializer,TechnicalEvaluationDashboardSerializer
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Max
from dynamic_form.models import FormSubmission
from configuration.models import Application, ScreeningCommittee
from screening.models import ScreeningRecord, TechnicalScreeningRecord

from rest_framework.views import APIView
from milestones.models import Milestone
from django.contrib.auth import get_user_model
from dynamic_form.serializers import FormSubmissionSerializer
from django.core.exceptions import FieldError

# views.py
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication

from dynamic_form.models import FormSubmission
from .models import EvaluationAssignment
from .serializers import EvaluationSubmitSerializer
# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import EvaluationAssignment
from .serializers import (
    AssignmentCreateSerializer,
    EvaluationSubmitSerializer,
    EvaluationAssignmentSerializer,
)
from rest_framework.permissions import IsAuthenticated
from .models import FormSubmission  # Assuming it exists


User = get_user_model()


 

class TechnicalEvaluationDashboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/screening/evaluation/ → items ready for technical evaluation
    """
    serializer_class   = TechnicalEvaluationDashboardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            FormSubmission.objects
                # .filter(screening_records__admin_decision="accepted")
                # .exclude(screening_records__technical_record__isnull=False)
                .distinct()
        )

        # 2) pick submissions that passed admin screening but not yet technically screened


class AssignEvaluatorViewSet(viewsets.GenericViewSet,
                             viewsets.mixins.CreateModelMixin):
    serializer_class   = AssignmentCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Handles bulk creation of assignments."""
        return super().create(request, *args, **kwargs)
    
    

@method_decorator(csrf_exempt, name='dispatch')
class EvaluateProposalViewSet(viewsets.ModelViewSet):
    """
    A CRUD API for evaluators to list/retrieve/update their own evaluations,
    plus a detail-route POST for evaluate.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAuthenticated]
    serializer_class       = EvaluationSubmitSerializer

    lookup_field           = 'form_submission__proposal_id'
    lookup_url_kwarg       = 'proposal_id'
    lookup_value_regex     = '.+'

    def get_queryset(self):
        return EvaluationAssignment.objects.filter(
            evaluator=self.request.user
        ).select_related('form_submission')

    def _enrich(self, assignment, serialized_data):
        return {
            "proposal_id": assignment.form_submission.proposal_id,
            "evaluator": {
                "id": assignment.evaluator.id,
                "email": assignment.evaluator.email,
                "name": getattr(assignment.evaluator, 'full_name', assignment.evaluator.email)
            },
            "evaluation": serialized_data
        }

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        items = page if page is not None else qs
        enriched = [self._enrich(obj, self.get_serializer(obj).data) for obj in items]
        return self.get_paginated_response(enriched) if page is not None else Response(enriched)

    def retrieve(self, request, *args, **kwargs):
        assignment = self.get_object()
        return Response(self._enrich(assignment, self.get_serializer(assignment).data))

    @action(detail=True, methods=['post'], url_path='evaluate')
    def evaluate(self, request, proposal_id=None):
        # POST /.../evaluation/{proposal_id}/evaluate/
        try:
            assignment = self.get_queryset().get(
                form_submission__proposal_id=proposal_id
            )
        except EvaluationAssignment.DoesNotExist:
            return Response({"error": "No assignment found for you."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(assignment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(evaluated_at=timezone.now())
        return Response(self._enrich(assignment, serializer.data), status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        # allow PUT/PATCH on detail
        partial = kwargs.pop('partial', False)
        assignment = self.get_object()
        serializer = self.get_serializer(assignment, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(evaluated_at=timezone.now())
        return Response(self._enrich(assignment, serializer.data))

    def destroy(self, request, *args, **kwargs):
        # optional: allow evaluators to clear their evaluation
        assignment = self.get_object()
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@method_decorator(csrf_exempt, name='dispatch')
class PassingRequirementViewSet(viewsets.ModelViewSet):
    queryset = PassingRequirement.objects.all()
    serializer_class = PassingRequirementSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response({
                "success": "true",
                "message": "Minimum marks added successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({
                "success": "false",
                "message": "Requirement name already exists.",
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({
                "success": "true",
                "message": "Minimum marks updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({
                "success": "false",
                "message": e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

class EvaluationItemViewSet(viewsets.ModelViewSet):
    queryset = EvaluationItem.objects.all()
    serializer_class = EvaluationItemSerializer
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return GeneralPoolItemSerializer 
        return EvaluationItemSerializer
    
     

    @action(detail=False, methods=['get'], url_path='config')
    def get_config(self, request):
        data = {
            "name": " ",
            "status": "Active",
            "Final_Status_minimum": "4%",
            "Presentation_max_marks": "3",
            "Presentation_minimum_percent": "2%",
            "evaluation_minimum": "1%"
        }
        return Response(data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data

        instance.name = data.get("name")
        instance.key = data.get("key")
        instance.total_marks = data.get("allocated")
        instance.weightage = data.get("weightage")
        instance.status = data.get("status", "Active")
        instance.description = data.get("description", "")
        instance.memberType = data.get("memberType")
        instance.type = data.get("type")
        instance.save()

        return Response({"message": f"{instance.type.capitalize()} updated successfully"}, status=status.HTTP_200_OK)

class EvaluationItemCreateView(APIView):
    def post(self, request):
        data = request.data
        item_type = data.get("type", "").strip()

        if item_type not in ["criteria", "question"]:
            return Response(
                {"error": "Invalid type. Must be 'criteria' or 'question'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            item = EvaluationItem.objects.create(
                name=data.get("name"),
                key=data.get("key"),
                total_marks=data.get("allocated"),
                weightage=data.get("weightage"),
                status=data.get("status", "Active"),
                description=data.get("description", ""),
                memberType=data.get("memberType"),
                type=item_type,
                created_by=request.user if request.user.is_authenticated else None
            )
            return Response(
                {"message": f"{item_type.capitalize()} created successfully", "id": item.id},
                status=status.HTTP_201_CREATED
            )

        except IntegrityError:
            return Response(
                {"error": f"A {item_type} with this key already exists. Please use a unique key."},
                status=status.HTTP_400_BAD_REQUEST
            )

class CriteriaTypeViewSet(viewsets.ModelViewSet):
    queryset = CriteriaType.objects.all()
    serializer_class = CriteriaTypeSerializer

class FormSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing and retrieving FormSubmissions.
    This replaces the ProposalViewSet.
    """
    queryset = FormSubmission.objects.all()
    serializer_class = TechnicalEvaluationSerializer
    
    def get_queryset(self):
        return FormSubmission.objects.all().order_by('-id')

class EvaluatorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/users/evaluators/  → [{"user":"alice@example.com"}, ...]
    """
    serializer_class = EvaluatorEmailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only users who have the 'evaluator' role (case-insensitive)
        return User.objects.filter(roles__name__iexact='evaluator')

class EvaluationAssignmentViewSet(viewsets.ModelViewSet):
    queryset = EvaluationAssignment.objects.all()
    serializer_class = EvaluationAssignmentSerializer
    
    def get_queryset(self):
        return EvaluationAssignment.objects.select_related(
            'form_submission', 'evaluator', 'evaluator__user'
        )

class CriteriaEvaluationViewSet(viewsets.ModelViewSet):
    queryset = CriteriaEvaluation.objects.all()
    serializer_class = CriteriaEvaluationSerializer
    
    def get_queryset(self):
        return CriteriaEvaluation.objects.select_related(
            'assignment', 'criteria', 'assignment__form_submission', 'assignment__evaluator'
        )

class QuestionEvaluationViewSet(viewsets.ModelViewSet):
    queryset = QuestionEvaluation.objects.all()
    serializer_class = QuestionEvaluationSerializer
    
    def get_queryset(self):
        return QuestionEvaluation.objects.select_related(
            'assignment', 'question', 'assignment__form_submission', 'assignment__evaluator'
        )

class EvaluationCutoffViewSet(viewsets.ModelViewSet):
    queryset = EvaluationCutoff.objects.all()
    serializer_class = EvaluationCutoffSerializer
    
    def get_queryset(self):
        return EvaluationCutoff.objects.select_related('form_submission')

class TechnicalEvaluationListView(ListAPIView):
    """
    API endpoint that lists technical evaluations in the required format.
    """
    serializer_class = TechnicalEvaluationSerializer

    def get_queryset(self):
        # 1) Gather all the FormSubmission PKs we care about
        screened_ids  = ScreeningRecord.objects.values_list('proposal_id', flat=True)
        evaluated_ids = EvaluationAssignment.objects.values_list('form_submission_id', flat=True)
        form_ids      = set(screened_ids) | set(evaluated_ids)

        # 2) Pull your FormSubmissions, with only valid prefetch paths
        return FormSubmission.objects.filter(
            id__in=form_ids
        ).prefetch_related(
            # admin-screening side
            'screening_records',
            'screening_records__technical_record',

            # evaluation side
            'eval_assignments',                         # all assignments
            'eval_assignments__evaluator',              # this is the User FK
            'eval_assignments__criteria_evaluations__criteria',
        ).order_by('-id')
    
    
class FormSubmissionSearchView(APIView):
    """
    API endpoint for searching FormSubmissions to populate dropdowns.
    """
    def get(self, request):
        query = request.query_params.get('q', '')
        limit = int(request.query_params.get('limit', 10))
        
        if not query:
            return Response([])
        
        # Search by form_id, title, subject, or other relevant fields
        forms = FormSubmission.objects.filter(
            form_id__icontains=query
        )[:limit]
        
        # Try to search by other fields if they exist
        for field in ['subject', 'title', 'name']:
            if hasattr(FormSubmission, field):
                forms = forms | FormSubmission.objects.filter(
                    **{f"{field}__icontains": query}
                )[:limit]
        
        # Format results for dropdown
        results = []
        for form in forms:
            label = ""
            # Try to get a good label using known fields
            for field in ['subject', 'title', 'name']:
                if hasattr(form, field) and getattr(form, field):
                    label = getattr(form, field)
                    break
            
            if not label:
                label = f"Form {form.form_id}"
                
            results.append({
                'id': form.id,
                'text': f"{label} ({form.form_id})"
            })
        
        return Response(results)
    

# app_eval/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import EvaluationItem
from .serializers import CriteriaDetailSerializer

class CriteriaListView(APIView):
    def get(self, request):
        try:
            queryset = EvaluationItem.objects.filter(type='criteria')
            serializer = CriteriaDetailSerializer(queryset, many=True)
            data = serializer.data

            return Response({
                "message": "Criteria items fetched successfully.",
                "success": True,
                "data": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "message": f"Failed to fetch criteria items: {str(e)}",
                "success": False,
                "data": None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


