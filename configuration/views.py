from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from .models import ScreeningCommittee, CommitteeMember, ScreeningResult
from .serializers import (
    ScreeningCommitteeSerializer, CommitteeMemberSerializer, 
    ScreeningResultSerializer, UserBasicSerializer,CommitteeSimpleSerializer
)
from .models import CriteriaEvaluatorAssignment
from .models import (
    Service, ServiceForm, EvaluationStage, 
    EvaluationCriteriaConfig, EvaluatorAssignment,
    Application, ApplicationStageProgress
)
from .serializers import (
    UserSerializer, ServiceSerializer, ServiceFormSerializer,
    EvaluationStageSerializer, EvaluationCriteriaConfigSerializer,
    EvaluatorAssignmentSerializer, ApplicationSerializer,
    ApplicationStageProgressSerializer
)
from rest_framework.generics import ListAPIView 

User = get_user_model()

# Custom permissions
class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superadmin

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin

class IsEvaluatorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_evaluator or request.user.is_admin)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsSuperAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superadmin:
            return User.objects.all()
        
        if user.is_admin:
            return User.objects.exclude(role='superadmin')
        
        return User.objects.filter(id=user.id)
        
    @action(detail=False, methods=['get'])
    def admins(self, request):
        admins = User.objects.filter(role='admin')
        serializer = self.get_serializer(admins, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def evaluators(self, request):
        evaluators = User.objects.filter(role='evaluator')
        serializer = self.get_serializer(evaluators, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def applicants(self, request):
        applicants = User.objects.filter(role='applicant')
        serializer = self.get_serializer(applicants, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
 

# views.py

# Updated

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSuperAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        # Superadmins see all, others see only active services within date window
        if user.is_superuser or getattr(user, 'is_superadmin', False):
            return Service.objects.all()
        return Service.objects.filter(
            status='active',
            is_active=True,
            start_date__lte=now,
        ).exclude(end_date__lt=now)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        data = serializer.data
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "Service created successfully.",
            "service": data
        }, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            "message": "Service updated successfully.",
            "service": serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Service deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        # Only allow non-superadmins to view if service is currently active
        if not (user.is_superuser or getattr(user, 'is_superadmin', False)):
            if not instance.is_currently_active:
                return Response(
                    {"error": "This service is not currently active."},
                    status=status.HTTP_403_FORBIDDEN
                )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # --- Custom actions below are unchanged, but included for reference ---

    @action(detail=True, methods=['get'])
    def forms(self, request, pk=None):
        service = self.get_object()
        forms = service.forms.all()
        from .serializers import ServiceFormSerializer
        serializer = ServiceFormSerializer(forms, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stages(self, request, pk=None):
        service = self.get_object()
        stages = service.evaluation_stages.all().order_by('order')
        from .serializers import EvaluationStageSerializer
        serializer = EvaluationStageSerializer(stages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        service = self.get_object()
        applications = service.applications.all()
        from .serializers import ApplicationSerializer
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['get'])
    def criteria(self, request, pk=None):
        service = self.get_object()
        from .models import EvaluationStage
        from .serializers import EvaluationCriteriaConfigSerializer

        detailed_stage = service.evaluation_stages.filter(
            name__icontains='detailed', 
            is_active=True
        ).first()
        if not detailed_stage:
            detailed_stage = EvaluationStage.objects.create(
                service=service,
                name="Detailed Evaluation",
                order=1,
                is_active=True,
                created_by=request.user
            )
        criteria = detailed_stage.criteria_configs.all()
        serializer = EvaluationCriteriaConfigSerializer(criteria, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def set_cutoff(self, request, pk=None):
        service = self.get_object()
        cutoff_score = request.data.get('cutoff_score')
        from .models import EvaluationStage

        if cutoff_score is None:
            return Response(
                {"error": "Cutoff score is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        detailed_stage = service.evaluation_stages.filter(
            name__icontains='detailed', 
            is_active=True
        ).first()
        if not detailed_stage:
            detailed_stage = EvaluationStage.objects.create(
                service=service,
                name="Detailed Evaluation",
                order=1,
                is_active=True,
                created_by=request.user
            )
        detailed_stage.cutoff_marks = cutoff_score
        detailed_stage.save()
        return Response({
            "message": "Cutoff score updated successfully",
            "service": service.name,
            "cutoff_score": cutoff_score
        })


class ServiceFormViewSet(viewsets.ModelViewSet):
    queryset = ServiceForm.objects.all()
    serializer_class = ServiceFormSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        service_id = self.request.query_params.get('service', None)
        if service_id:
            return ServiceForm.objects.filter(service_id=service_id)
        return ServiceForm.objects.all()


class EvaluationStageViewSet(viewsets.ModelViewSet):
    queryset = EvaluationStage.objects.all().order_by('service', 'order')
    serializer_class = EvaluationStageSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        service_id = self.request.query_params.get('service', None)
        if service_id:
            return EvaluationStage.objects.filter(service_id=service_id).order_by('order')
        return EvaluationStage.objects.all().order_by('service', 'order')
    
    @action(detail=True, methods=['get'])
    def criteria(self, request, pk=None):
        stage = self.get_object()
        criteria = stage.criteria_configs.all()
        serializer = EvaluationCriteriaConfigSerializer(criteria, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def evaluators(self, request, pk=None):
        stage = self.get_object()
        evaluators = stage.evaluators.filter(is_active=True)
        serializer = EvaluatorAssignmentSerializer(evaluators, many=True)
        return Response(serializer.data)


class EvaluationCriteriaConfigViewSet(viewsets.ModelViewSet):
    queryset = EvaluationCriteriaConfig.objects.all()
    serializer_class = EvaluationCriteriaConfigSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        stage_id = self.request.query_params.get('stage', None)
        service_id = self.request.query_params.get('service', None)
        
        queryset = EvaluationCriteriaConfig.objects.all()
        
        if stage_id:
            return queryset.filter(stage_id=stage_id)
        
        if service_id:
            # For the simplified flow, get criteria from the detailed evaluation stage
            service = Service.objects.get(id=service_id)
            detailed_stage = service.evaluation_stages.filter(
                name__icontains='detailed',
                is_active=True
            ).first()
            
            if detailed_stage:
                return queryset.filter(stage=detailed_stage)
            return EvaluationCriteriaConfig.objects.none()
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        # Handle the simplified flow when service is provided instead of stage
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        
        if 'service' in data and 'stage' not in data:
            try:
                service = Service.objects.get(id=data['service'])
                # Get or create detailed evaluation stage
                detailed_stage = service.evaluation_stages.filter(
                    name__icontains='detailed',
                    is_active=True
                ).first()
                
                if not detailed_stage:
                    detailed_stage = EvaluationStage.objects.create(
                        service=service,
                        name="Detailed Evaluation",
                        order=1,
                        is_active=True,
                        created_by=request.user
                    )
                
                data['stage'] = str(detailed_stage.id)
                # Remove service as it's not part of the serializer
                data.pop('service', None)
            except Service.DoesNotExist:
                return Response(
                    {"error": "Service not found"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Make criteria_type field optional
        if 'criteria_type' not in data:
            data['criteria_type'] = None
        
        # Use the modified data for serialization
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        # Create a copy of the data to avoid modifying the original
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        
        # Handle service to stage conversion for simplified flow
        if 'service' in data and 'stage' not in data:
            try:
                service = Service.objects.get(id=data['service'])
                detailed_stage = service.evaluation_stages.filter(
                    name__icontains='detailed',
                    is_active=True
                ).first()
                
                if detailed_stage:
                    data['stage'] = str(detailed_stage.id)
                # Remove service as it's not part of the serializer
                data.pop('service', None)
            except Service.DoesNotExist:
                return Response(
                    {"error": "Service not found"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Make criteria_type field optional
        if 'criteria_type' not in data:
            data['criteria_type'] = None
        
        # Get the instance to update
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Use the modified data for serialization
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def evaluators(self, request, pk=None):
        """Get all evaluators assigned to this criterion"""
        criterion = self.get_object()
        assignments = CriteriaEvaluatorAssignment.objects.filter(
           criteria=criterion,
           is_active=True
        ).select_related('evaluator')
    
        evaluators = [assignment.evaluator for assignment in assignments]
        serializer = UserSerializer(evaluators, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def assign_evaluators(self, request, pk=None):
        """Assign multiple evaluators to this criterion"""
        criterion = self.get_object()
        evaluator_ids = request.data.get('evaluator_ids', [])
    
        if not evaluator_ids:
           return Response(
            {"error": "No evaluator IDs provided"}, 
            status=status.HTTP_400_BAD_REQUEST
           )
    
        
        evaluators = User.objects.filter(id__in=evaluator_ids)
        if len(evaluators) != len(evaluator_ids):
           return Response(
             {"error": "One or more evaluator IDs are invalid"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
        
        CriteriaEvaluatorAssignment.objects.filter(
           criteria=criterion,
           is_active=True
        ).update(is_active=False)
    
        
        assignments = []
        for evaluator in evaluators:
            assignment, created = CriteriaEvaluatorAssignment.objects.get_or_create(
              criteria=criterion,
              evaluator=evaluator,
              defaults={
                'assigned_by': request.user,
                'is_active': True
            }
        )
        
            if not created:
                
                assignment.is_active = True
                assignment.assigned_by = request.user
                assignment.assigned_at = timezone.now()
                assignment.save()
            
            assignments.append(assignment)
    
        return Response(
         {"message": f"Successfully assigned {len(assignments)} evaluators to this criterion"},
        status=status.HTTP_200_OK
    )

    @action(detail=True, methods=['delete'], url_path='evaluators/(?P<evaluator_id>[^/.]+)')
    def remove_evaluator(self, request, pk=None, evaluator_id=None):
        """Remove a specific evaluator from this criterion"""
        criterion = self.get_object()
    
        try:
            assignment = CriteriaEvaluatorAssignment.objects.get(
                criteria=criterion,
                evaluator_id=evaluator_id,
                is_active=True
            )
        
            assignment.is_active = False
            assignment.save()
        
            return Response(
                {"message": "Evaluator removed from criterion successfully"},
                status=status.HTTP_200_OK
            )
        except CriteriaEvaluatorAssignment.DoesNotExist:
            return Response(
                {"error": "Evaluator is not assigned to this criterion"},
                status=status.HTTP_404_NOT_FOUND
            )
    queryset = EvaluationCriteriaConfig.objects.all()
    serializer_class = EvaluationCriteriaConfigSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        stage_id = self.request.query_params.get('stage', None)
        if stage_id:
            return EvaluationCriteriaConfig.objects.filter(stage_id=stage_id)
        return EvaluationCriteriaConfig.objects.all()
    
    def create(self, request, *args, **kwargs):
        
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        
        
        if 'criteria_type' not in data:
            data['criteria_type'] = None
        
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        
        
        if 'criteria_type' not in data:
            data['criteria_type'] = None
        
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        lization
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def evaluators(self, request, pk=None):
        """Get all evaluators assigned to this criterion"""
        criterion = self.get_object()
        assignments = CriteriaEvaluatorAssignment.objects.filter(
           criteria=criterion,
           is_active=True
        ).select_related('evaluator')
    
        evaluators = [assignment.evaluator for assignment in assignments]
        serializer = UserSerializer(evaluators, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def assign_evaluators(self, request, pk=None):
        """Assign multiple evaluators to this criterion"""
        criterion = self.get_object()
        evaluator_ids = request.data.get('evaluator_ids', [])
    
        if not evaluator_ids:
           return Response(
            {"error": "No evaluator IDs provided"}, 
            status=status.HTTP_400_BAD_REQUEST
           )
    
    
        evaluators = User.objects.filter(id__in=evaluator_ids)
        if len(evaluators) != len(evaluator_ids):
           return Response(
             {"error": "One or more evaluator IDs are invalid"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    
        CriteriaEvaluatorAssignment.objects.filter(
           criteria=criterion,
           is_active=True
    ).update(is_active=False)
    
    
        assignments = []
        for evaluator in evaluators:
            assignment, created = CriteriaEvaluatorAssignment.objects.get_or_create(
              criteria=criterion,
              evaluator=evaluator,
              defaults={
                'assigned_by': request.user,
                'is_active': True
            }
        )
        
            if not created:
            # If it exists but was deactivated, reactivate it
               assignment.is_active = True
               assignment.assigned_by = request.user
               assignment.assigned_at = timezone.now()
               assignment.save()
            
            assignments.append(assignment)
    
        return Response(
         {"message": f"Successfully assigned {len(assignments)} evaluators to this criterion"},
        status=status.HTTP_200_OK
    )

    @action(detail=True, methods=['delete'], url_path='evaluators/(?P<evaluator_id>[^/.]+)')
    def remove_evaluator(self, request, pk=None, evaluator_id=None):
        """Remove a specific evaluator from this criterion"""
        criterion = self.get_object()
    
        try:
            assignment = CriteriaEvaluatorAssignment.objects.get(
            criteria=criterion,
            evaluator_id=evaluator_id,
            is_active=True
        )
        
            assignment.is_active = False
            assignment.save()
        
            return Response(
             {"message": "Evaluator removed from criterion successfully"},
            status=status.HTTP_200_OK
        )
        except CriteriaEvaluatorAssignment.DoesNotExist:
            return Response(
              {"error": "Evaluator is not assigned to this criterion"},
            status=status.HTTP_404_NOT_FOUND
        )    


class EvaluatorAssignmentViewSet(viewsets.ModelViewSet):
    queryset = EvaluatorAssignment.objects.all()
    serializer_class = EvaluatorAssignmentSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin:
            stage_id = self.request.query_params.get('stage', None)
            if stage_id:
                return EvaluatorAssignment.objects.filter(stage_id=stage_id)
            return EvaluatorAssignment.objects.all()
        
        if user.is_evaluator:
            return EvaluatorAssignment.objects.filter(user=user)
        
        return EvaluatorAssignment.objects.none()


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['applicant__username', 'applicant__first_name', 'applicant__last_name', 'service__name']
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin:
            service_id = self.request.query_params.get('service', None)
            if service_id:
                return Application.objects.filter(service_id=service_id)
            return Application.objects.all()
        
        if user.is_evaluator:
            assigned_stages = EvaluatorAssignment.objects.filter(user=user, is_active=True).values_list('stage_id', flat=True)
            return Application.objects.filter(
                Q(current_stage_id__in=assigned_stages) & 
                Q(status='under_evaluation')
            )
        
        return Application.objects.filter(applicant=user)
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        application = self.get_object()
        progress = application.stage_progress.all()
        serializer = ApplicationStageProgressSerializer(progress, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        application = self.get_object()
        
        if application.applicant != request.user and not request.user.is_admin:
            return Response(
                {"error": "You don't have permission to submit this application"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if application.status != 'draft':
            return Response(
                {"error": "This application has already been submitted"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not application.form_submission:
            return Response(
                {"error": "No form submission attached to this application"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        
        application.status = 'submitted'
        application.submitted_at = timezone.now()
        
        first_stage = application.service.evaluation_stages.filter(
            is_active=True
        ).order_by('order').first()
        
        if first_stage:
            application.current_stage = first_stage
            
            ApplicationStageProgress.objects.create(
                application=application,
                stage=first_stage,
                status='pending'
            )
        
        application.save()
        
        serializer = self.get_serializer(application)
        return Response(serializer.data)


class ApplicationStageProgressViewSet(viewsets.ModelViewSet):
    queryset = ApplicationStageProgress.objects.all()
    serializer_class = ApplicationStageProgressSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        application_id = self.request.query_params.get('application', None)
        if application_id:
            return ApplicationStageProgress.objects.filter(application_id=application_id)
        return ApplicationStageProgress.objects.all()
    
    @action(detail=True, methods=['post'])
    def start_evaluation(self, request, pk=None):
        progress = self.get_object()
        
        user = request.user
        is_assigned = EvaluatorAssignment.objects.filter(
            user=user,
            stage=progress.stage,
            is_active=True
        ).exists()
        
        if not is_assigned and not user.is_admin:
            return Response(
                {"error": "You are not assigned as an evaluator for this stage"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if progress.status != 'pending':
            return Response(
                {"error": "This stage is not pending evaluation"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        
        progress.status = 'in_progress'
        progress.start_date = timezone.now()
        progress.save()
        
        serializer = self.get_serializer(progress)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete_evaluation(self, request, pk=None):
        progress = self.get_object()
        total_score = request.data.get('total_score')
        
        user = request.user
        is_assigned = EvaluatorAssignment.objects.filter(
            user=user,
            stage=progress.stage,
            is_active=True
        ).exists()
        
        if not is_assigned and not user.is_admin:
            return Response(
                {"error": "You are not assigned as an evaluator for this stage"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if progress.status != 'in_progress':
            return Response(
                {"error": "This stage is not in progress"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if total_score is None:
            return Response(
                {"error": "Total score is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        
        
        status_value = 'passed' if float(total_score) >= float(progress.stage.cutoff_marks) else 'failed'
        
        progress.status = status_value
        progress.completion_date = timezone.now()
        progress.total_score = total_score
        progress.save()
        
        application = progress.application
        
        if status_value == 'passed':
            next_stage = EvaluationStage.objects.filter(
                service=application.service,
                order__gt=progress.stage.order,
                is_active=True
            ).order_by('order').first()
            
            if next_stage:
                
                application.current_stage = next_stage
                application.save()
                
                
                ApplicationStageProgress.objects.create(
                    application=application,
                    stage=next_stage,
                    status='pending'
                )
            else:
                
                application.status = 'approved'
                application.current_stage = None
                application.save()
        else:
            application.status = 'rejected'
            application.save()
        
        serializer = self.get_serializer(progress)
        return Response(serializer.data)
    

class ScreeningCommitteeViewSet(viewsets.ModelViewSet):
    queryset = ScreeningCommittee.objects.all()
    serializer_class = ScreeningCommitteeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description', 'committee_type']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        service_id = self.request.query_params.get('service', None)
        committee_type = self.request.query_params.get('type', None)
        
        queryset = ScreeningCommittee.objects.all()
        
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        
        if committee_type:
            queryset = queryset.filter(committee_type=committee_type)
            
        return queryset
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        committee = self.get_object()
        members = committee.members.filter(is_active=True)
        serializer = CommitteeMemberSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def set_head(self, request, pk=None):
        committee = self.get_object()
        user_id = request.data.get('user_id')
        
        if user_id is None:  # Handle null case for removing head
            committee.head = None
            committee.save()
            return Response({"message": "Head removed successfully"})
            
        try:
            user_id = int(user_id)
            user = User.objects.get(id=user_id)
            
            
            is_member = committee.members.filter(user_id=user_id, is_active=True).exists()
            
            if not is_member:
                
                CommitteeMember.objects.create(
                    committee=committee,
                    user=user,
                    assigned_by=request.user,
                    is_active=True
                )
            
            
            committee.head = user
            committee.save()
            
            return Response({"message": "Head assigned successfully"})
        except User.DoesNotExist:
            return Response(
                {"error": "User does not exist"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Error assigning head: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def set_sub_head(self, request, pk=None):
        committee = self.get_object()
        user_id = request.data.get('user_id')
        
        if user_id is None:  
            committee.sub_head = None
            committee.save()
            return Response({"message": "Sub-head removed successfully"})
            
        try:
            user_id = int(user_id)
            user = User.objects.get(id=user_id)
            
            
            if committee.head and committee.head.id == user_id:
                return Response(
                    {"error": "Head and Sub-head must be different users"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            t
            is_member = committee.members.filter(user_id=user_id, is_active=True).exists()
            
            if not is_member:
                
                CommitteeMember.objects.create(
                    committee=committee,
                    user=user,
                    assigned_by=request.user,
                    is_active=True
                )
            
            # Set as sub-head
            committee.sub_head = user
            committee.save()
            
            return Response({"message": "Sub-head assigned successfully"})
        except User.DoesNotExist:
            return Response(
                {"error": "User does not exist"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Error assigning sub-head: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def available_members(self, request, pk=None):
        committee = self.get_object()
        
        
        existing_members = list(committee.members.filter(is_active=True).values_list('user_id', flat=True))
        
        
        if committee.head and committee.head.id not in existing_members:
            existing_members.append(committee.head.id)
        
        if committee.sub_head and committee.sub_head.id not in existing_members:
            existing_members.append(committee.sub_head.id)
        
        available_users = User.objects.filter(role='evaluator').exclude(id__in=existing_members)
        
        serializer = UserBasicSerializer(available_users, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def screenings(self, request, pk=None):
        committee = self.get_object()
        screenings = committee.screenings.all()
        serializer = ScreeningResultSerializer(screenings, many=True)
        return Response(serializer.data)


class CommitteeMemberViewSet(viewsets.ModelViewSet):
    queryset = CommitteeMember.objects.all()
    serializer_class = CommitteeMemberSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        committee_id = self.request.query_params.get('committee', None)
        user_id = self.request.query_params.get('user', None)
        
        queryset = CommitteeMember.objects.all()
        
        if committee_id:
            queryset = queryset.filter(committee_id=committee_id)
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)
        
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        committee = instance.committee
        user_id = instance.user.id
        
        
        if committee.head and committee.head.id == user_id:
            committee.head = None
            committee.save()
        
        if committee.sub_head and committee.sub_head.id == user_id:
            committee.sub_head = None
            committee.save()
        
        
        
        return super().destroy(request, *args, **kwargs)


class ScreeningResultViewSet(viewsets.ModelViewSet):
    queryset = ScreeningResult.objects.all()
    serializer_class = ScreeningResultSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsEvaluatorOrAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        
        
        if user.is_admin:
            application_id = self.request.query_params.get('application', None)
            committee_id = self.request.query_params.get('committee', None)
            
            queryset = ScreeningResult.objects.all()
            
            if application_id:
                queryset = queryset.filter(application_id=application_id)
            
            if committee_id:
                queryset = queryset.filter(committee_id=committee_id)
                
            return queryset
        
        
        elif user.is_evaluator:
            committee_ids = CommitteeMember.objects.filter(
                user=user, 
                is_active=True
            ).values_list('committee_id', flat=True)
            
            return ScreeningResult.objects.filter(committee_id__in=committee_ids)
        
        
        else:
            return ScreeningResult.objects.filter(application__applicant=user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        screening = self.get_object()
        
        
        user = request.user
        if not user.is_admin and not CommitteeMember.objects.filter(
            user=user, 
            committee=screening.committee,
            is_active=True
        ).exists():
            return Response(
                {"error": "You are not a member of this screening committee"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        notes = request.data.get('notes', '')
        
        screening.result = 'approved'
        screening.notes = notes
        screening.screened_by = user
        
        from django.utils import timezone
        screening.screened_at = timezone.now()
        screening.save()
        
        
        application = screening.application
        
        if screening.committee.committee_type == 'administrative':
            
            application.status = 'technical_screening'
            application.save()
            
            
            try:
                technical_committee = ScreeningCommittee.objects.get(
                    service=application.service,
                    committee_type='technical',
                    is_active=True
                )
                
                ScreeningResult.objects.get_or_create(
                    application=application,
                    committee=technical_committee,
                    defaults={'result': 'pending'}
                )
                
            except ScreeningCommittee.DoesNotExist:
                
                pass
            
        elif screening.committee.committee_type == 'technical':
            
            application.status = 'under_evaluation'
            
            
            first_stage = application.service.evaluation_stages.filter(
                is_active=True
            ).order_by('order').first()
            
            if first_stage:
                application.current_stage = first_stage
                
                from .models import ApplicationStageProgress
                ApplicationStageProgress.objects.get_or_create(
                    application=application,
                    stage=first_stage,
                    defaults={'status': 'pending'}
                )
            
            application.save()
        
        serializer = self.get_serializer(screening)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        screening = self.get_object()
        
        
        user = request.user
        if not user.is_admin and not CommitteeMember.objects.filter(
            user=user, 
            committee=screening.committee,
            is_active=True
        ).exists():
            return Response(
                {"error": "You are not a member of this screening committee"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        
        reject_reason = request.data.get('notes', '')
        if not reject_reason:
            return Response(
                {"error": "Rejection reason is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        screening.result = 'rejected'
        screening.notes = reject_reason
        screening.screened_by = user
        
        from django.utils import timezone
        screening.screened_at = timezone.now()
        screening.save()
        
        
        application = screening.application
        application.status = 'rejected'
        application.save()
        
        serializer = self.get_serializer(screening)
        return Response(serializer.data)
    
# New
# API

from rest_framework.pagination import PageNumberPagination
class CommitteePagination(PageNumberPagination):
    page_size = 20
    # page_size_query_param = 'page_size'
    max_page_size = 200  # Optional, prevents abuse

class CommitteeListAPIView(ListAPIView):
    queryset = ScreeningCommittee.objects.filter(is_active=True)
    serializer_class = CommitteeSimpleSerializer
    pagination_class = CommitteePagination

    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs)
            if isinstance(response.data, dict):  # Paginated response
                return Response({
                    "success": True,
                    "message": "Committees fetched successfully.",
                    "count": response.data.get('count', len(response.data.get('results', []))),
                    "next": response.data.get('next'),
                    "previous": response.data.get('previous'),
                    "data": response.data.get('results')
                }, status=status.HTTP_200_OK)
            elif isinstance(response.data, list):  # Non-paginated
                return Response({
                    "success": True,
                    "message": "Committees fetched successfully.",
                    "count": len(response.data),
                    "next": None,
                    "previous": None,
                    "data": response.data
                }, status=status.HTTP_200_OK)
            else:  # Fallback
                return Response({
                    "success": True,
                    "message": "Committees fetched successfully.",
                    "count": 0,
                    "next": None,
                    "previous": None,
                    "data": []
                }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Error occurred: {str(e)}",
                "count": 0,
                "next": None,
                "previous": None,
                "data": []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import EvaluationCriteriaConfig

class CriteriaListAPIView(APIView):
    def get(self, request):
        try:
            queryset = EvaluationCriteriaConfig.objects.all()
            data = []
            for obj in queryset:
                data.append({
                    "id": obj.id,
                    "name": obj.name,
                    "description": obj.description or "",
                    "maxMarks": float(obj.total_marks),
                    "weight": float(obj.weight),
                })
            return Response({
                "success": True,
                "message": "Criteria fetched successfully.",
                "data": data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Error occurred: {str(e)}",
                "data": []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





# Fro Config

# configuration/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Service, ScreeningCommittee
from .serializers import ServiceConfigSerializer
from app_eval.models import EvaluationCutoff
from django.core.exceptions import ValidationError

class ServiceConfigViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().prefetch_related('evaluation_items')
    serializer_class = ServiceConfigSerializer
    permission_classes = [IsAuthenticated]

    def _get_or_create_passing_requirement(self, data, service=None, user=None, update=False):
        from app_eval.models import PassingRequirement

        passing_req_data = data.pop('passing_requirement', None)
        if not passing_req_data:
            return None

        req_id = passing_req_data.get('id')
        if req_id:
            req = PassingRequirement.objects.filter(id=req_id).first()
            if req:
                for f in [
                    'requirement_name', 'evaluation_min_passing', 'presentation_min_passing',
                    'presentation_max_marks', 'final_status_min_passing', 'status'
                ]:
                    if f in passing_req_data:
                        setattr(req, f, passing_req_data[f])
                req.save()
                return req
            elif update:
                # ID provided but not found: do not create a new one on update!
                return None
        elif update:
            # No ID provided, and we're updating: try to use the existing one attached to the service
            if service and getattr(service, "passing_requirement", None):
                req = service.passing_requirement
                for f in [
                    'requirement_name', 'evaluation_min_passing', 'presentation_min_passing',
                    'presentation_max_marks', 'final_status_min_passing', 'status'
                ]:
                    if f in passing_req_data:
                        setattr(req, f, passing_req_data[f])
                req.save()
                return req
            # No id and no existing: do not create a new one!
            return None
        else:
            # Only create if it's a new service
            if not passing_req_data.get('requirement_name') and service:
                passing_req_data['requirement_name'] = f"{service.name} Passing Config"
            req = PassingRequirement.objects.create(**passing_req_data)
            return req
        return None



    def _get_committee(self, committee_data, committee_type, service, user):
        """
        Handles both existing (ID) and new (dict) committee assignments.
        Returns the ScreeningCommittee instance or None.
        """
        if not committee_data:
            return None
        if isinstance(committee_data, int) or (isinstance(committee_data, str) and committee_data.isdigit()):
            # Existing committee by ID
            committee = ScreeningCommittee.objects.filter(id=committee_data, committee_type=committee_type).first()
            if committee:
                committee.service = service
                committee.committee_type = committee_type  # Defensive
                committee.save()
            return committee
        elif isinstance(committee_data, dict):
            # New committee by data
            return ScreeningCommittee.objects.create(
                name=committee_data.get('name'),
                committee_type=committee_type,
                created_by=user,
                service=service
            )
        return None

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user
        try:
            with transaction.atomic():
                # Prepare for committee assignment
                admin_committee_data = data.pop('admin_committee', None)
                tech_committee_data = data.pop('tech_committee', None)

                # Remove property fields that should not be set directly
                for k in ['is_active', 'is_currently_active']:
                    data.pop(k, None)

                # Create Service
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                service = serializer.save(created_by=user)

                # Assign committees (existing or new)
                admin_committee = self._get_committee(admin_committee_data, 'administrative', service, user)
                tech_committee = self._get_committee(tech_committee_data, 'technical', service, user)

                # PassingRequirement
                passing_req = self._get_or_create_passing_requirement(request.data, service=service, user=user)
                if passing_req:
                    service.passing_requirement = passing_req
                    service.save(update_fields=['passing_requirement'])

                # Evaluation Items
                evaluation_items = request.data.get('evaluation_items', [])
                if evaluation_items:
                    service.evaluation_items.set(evaluation_items)

                # Cutoff marks
                cutoff_marks = request.data.get('cutoff_marks')
                if cutoff_marks is not None:
                    EvaluationCutoff.objects.update_or_create(
                        service=service,
                        defaults={'cutoff_marks': cutoff_marks, 'created_by': user}
                    )

                # Presentation max marks (if still field on Service)
                presentation_max_marks = request.data.get('presentation_max_marks')
                if presentation_max_marks is not None and hasattr(service, 'presentation_max_marks'):
                    setattr(service, 'presentation_max_marks', presentation_max_marks)
                    service.save(update_fields=['presentation_max_marks'])

                response_serializer = self.get_serializer(service)
                return Response(
                    {
                        "message": "Service created successfully.",
                        "service": response_serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
        except (ValidationError, Exception) as e:
            return Response(
                {"message": f"Failed to create Service: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()
        user = request.user
        try:
            with transaction.atomic():
                admin_committee_data = data.pop('admin_committee', None)
                tech_committee_data = data.pop('tech_committee', None)
                for k in ['is_active', 'is_currently_active']:
                    data.pop(k, None)
                serializer = self.get_serializer(instance, data=data, partial=partial)
                serializer.is_valid(raise_exception=True)
                service = serializer.save()

                # Committees
                admin_committee = self._get_committee(admin_committee_data, 'administrative', service, user)
                tech_committee = self._get_committee(tech_committee_data, 'technical', service, user)

                # ⬇️ HERE: pass update=True!
                passing_req = self._get_or_create_passing_requirement(request.data, service=service, user=user, update=True)
                if passing_req:
                    service.passing_requirement = passing_req
                    service.save(update_fields=['passing_requirement'])

                # ... rest is same ...
                evaluation_items = request.data.get('evaluation_items', [])
                if evaluation_items:
                    service.evaluation_items.set(evaluation_items)

                cutoff_marks = request.data.get('cutoff_marks')
                if cutoff_marks is not None:
                    EvaluationCutoff.objects.update_or_create(
                        service=service,
                        defaults={'cutoff_marks': cutoff_marks, 'created_by': user}
                    )

                presentation_max_marks = request.data.get('presentation_max_marks')
                if presentation_max_marks is not None and hasattr(service, 'presentation_max_marks'):
                    setattr(service, 'presentation_max_marks', presentation_max_marks)
                    service.save(update_fields=['presentation_max_marks'])

                response_serializer = self.get_serializer(service)
                return Response(
                    {
                        "message": "Service updated successfully.",
                        "service": response_serializer.data
                    },
                    status=status.HTTP_200_OK
                )
        except (ValidationError, Exception) as e:
            return Response(
                {"message": f"Failed to update Service: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )




    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
            return Response(
                {"message": "Service deleted successfully."},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return Response(
                {"message": f"Failed to delete Service: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "message": "Service details retrieved.",
                "service": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True) if page is not None else self.get_serializer(queryset, many=True)
        data = serializer.data
        msg = f"Returned {len(data)} services."
        if page is not None:
            return self.get_paginated_response({"message": msg, "services": data})
        return Response(
            {
                "message": msg,
                "services": data
            },
            status=status.HTTP_200_OK
        )

