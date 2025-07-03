from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Service, ServiceForm, EvaluationStage, 
    EvaluationCriteriaConfig, EvaluatorAssignment,
    Application, ApplicationStageProgress
)
from .models import ScreeningCommittee, CommitteeMember, ScreeningResult,CriteriaEvaluatorAssignment
from dynamic_form.models import FormTemplate, FormField
from app_eval.models import CriteriaType

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'role', 'department', 'phone', 'is_active', 'date_joined']
        read_only_fields = ['date_joined']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class FormTemplateMinSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormTemplate
        fields = ['id', 'title']


# class ServiceSerializer(serializers.ModelSerializer):
#     created_by_name = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Service
#         fields = [
#             'id', 'name', 'description', 'is_active', 'status',  # added status
#             'created_by', 'created_by_name', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ['created_by', 'created_at', 'updated_at']

#     def get_created_by_name(self, obj):
#         if obj.created_by:
#             return obj.created_by.get_full_name() or obj.created_by.username
#         return None

#     def create(self, validated_data):
#         user = self.context['request'].user
#         validated_data['created_by'] = user
#         # If not provided, default status to 'draft'
#         if 'status' not in validated_data:
#             validated_data['status'] = 'draft'
#         return super().create(validated_data)

#     def update(self, instance, validated_data):
#         # Only update status if it's in data (for patch/final-save)
#         status = validated_data.get('status')
#         if status:
#             instance.status = status
#         return super().update(instance, validated_data)


class ServiceSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    is_currently_active = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'is_active', 'status',
            'start_date', 'end_date', 'schedule_date',
            'image', 'documents',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'is_currently_active',
        ]
        read_only_fields = [
            'created_by', 'created_by_name', 'created_at', 'updated_at', 'is_currently_active'
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def get_is_currently_active(self, obj):
        return obj.is_currently_active

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        # Default status to 'draft' if not provided
        if 'status' not in validated_data:
            validated_data['status'] = 'draft'
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Only update status if provided (optional)
        status = validated_data.get('status')
        if status:
            instance.status = status
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Return URLs for image and document fields
        if instance.image:
            data['image'] = instance.image.url
        if instance.documents:
            data['documents'] = instance.documents.url
        return data





class ServiceFormSerializer(serializers.ModelSerializer):
    form_template_details = FormTemplateMinSerializer(source='form_template', read_only=True)
    
    class Meta:
        model = ServiceForm
        fields = ['id', 'service', 'form_template', 'form_template_details', 
                 'is_active', 'created_by', 'created_at']
        read_only_fields = ['created_by', 'created_at']
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)


class EvaluationStageSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = EvaluationStage
        fields = ['id', 'service', 'service_name', 'name', 'description', 
                 'order', 'is_active', 'cutoff_marks', 'created_by', 
                 'created_by_name', 'created_at']
        read_only_fields = ['created_by', 'created_at']
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)
    
    def validate(self, data):
        if self.instance is None:  
            service = data.get('service')
            existing_stages = EvaluationStage.objects.filter(service=service).count()
            if existing_stages >= 3:
                raise serializers.ValidationError("A service can have a maximum of 3 evaluation stages.")
        return data


class FormFieldMinSerializer(serializers.ModelSerializer):
    page_title = serializers.CharField(source='page.title', read_only=True)
    
    class Meta:
        model = FormField
        fields = ['id', 'label', 'field_type', 'page_title']


class CriteriaTypeMinSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriteriaType
        fields = ['id', 'name']


# Modified EvaluationCriteriaConfigSerializer to remove stage requirement
class EvaluationCriteriaConfigSerializer(serializers.ModelSerializer):
    field_details = serializers.SerializerMethodField()
    assigned_evaluators = serializers.SerializerMethodField()
    
    class Meta:
        model = EvaluationCriteriaConfig
        fields = ['id', 'name', 'stage', 'field', 'field_details', 'criteria_type', 
                  'total_marks', 'weight', 'created_by', 'created_at', 'assigned_evaluators']
        # Make stage optional in the serializer
        extra_kwargs = {
            'stage': {'required': False}
        }
    
    def get_field_details(self, obj):
        if obj.field:
            return {
                'id': obj.field.id,
                'label': obj.field.label,
                'field_type': obj.field.field_type
            }
        return None
    
    def get_assigned_evaluators(self, obj):
        # Get all active evaluator assignments for this criteria
        assignments = CriteriaEvaluatorAssignment.objects.filter(
            criteria=obj,
            is_active=True
        ).select_related('evaluator')
        
        # Return simple representation of assigned evaluators
        return [{
            'id': assignment.evaluator.id,
            'name': assignment.evaluator.get_full_name() or assignment.evaluator.username
        } for assignment in assignments]
        
    def validate(self, data):
        # Check if the service field is provided instead of stage
        request = self.context.get('request')
        if request and request.data and 'service' in request.data and 'stage' not in data:
            try:
                from .models import Service, EvaluationStage
                service_id = request.data.get('service')
                service = Service.objects.get(id=service_id)
                
                # Get or create the detailed evaluation stage
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
                
                # Set the stage in the validated data
                data['stage'] = detailed_stage
            except Service.DoesNotExist:
                raise serializers.ValidationError({"service": ["Service not found"]})
            except Exception as e:
                raise serializers.ValidationError({"error": [str(e)]})
        
        return data
    
    
class EvaluatorAssignmentSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    stage_details = EvaluationStageSerializer(source='stage', read_only=True)
    
    class Meta:
        model = EvaluatorAssignment
        fields = ['id', 'user', 'user_details', 'stage', 'stage_details', 
                 'assigned_by', 'assigned_at', 'is_active']
        read_only_fields = ['assigned_by', 'assigned_at']
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['assigned_by'] = user
        return super().create(validated_data)
    
    def validate(self, data):
        # Ensure the assigned user has the evaluator role
        if data.get('user') and data.get('user').role != 'evaluator':
            raise serializers.ValidationError("The assigned user must have the evaluator role.")
        return data


class ApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='service.name', read_only=True)
    current_stage_name = serializers.CharField(source='current_stage.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Application
        fields = ['id', 'service', 'service_name', 'applicant', 'applicant_name',
                 'form_submission', 'status', 'submitted_at', 'current_stage', 
                 'current_stage_name']
        read_only_fields = ['submitted_at', 'current_stage']
    
    def get_applicant_name(self, obj):
        return obj.applicant.get_full_name() or obj.applicant.username


class ApplicationStageProgressSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    
    class Meta:
        model = ApplicationStageProgress
        fields = ['id', 'application', 'stage', 'stage_name', 'status',
                 'start_date', 'completion_date', 'total_score']
        read_only_fields = ['start_date', 'completion_date', 'total_score']


class UserBasicSerializer(serializers.ModelSerializer):
    # no `source` needed when the field name matches the model
    full_name = serializers.CharField(read_only=True)
    email     = serializers.EmailField(read_only=True)

    department = serializers.SerializerMethodField()
    role       = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'full_name', 'email', 'department', 'role']

    def get_department(self, obj):
        return getattr(obj, 'evaluator', None) and obj.evaluator.department

    def get_role(self, obj):
        ur = obj.userrole_set.first()
        return ur.role.name if ur else None


class CommitteeMemberSerializer(serializers.ModelSerializer):
    # nested user info
    user_details     = UserBasicSerializer(source='user', read_only=True)

    # new read-only fields pulled from the related ScreeningCommittee
    committee_name   = serializers.CharField(source='committee.name', read_only=True)
    member_type      = serializers.CharField(source='committee.member_type', read_only=True)

    class Meta:
        model  = CommitteeMember
        fields = [
            'id',
            'committee',        
            'committee_name',   
            'member_type',      
            'user',
            'user_details',
            'is_active',
            'assigned_at',      
        ]
        read_only_fields = ['assigned_at']

    def create(self, validated_data):
        # attach the current user as 'assigned_by'
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['assigned_by'] = request.user
        return super().create(validated_data)






from rest_framework import serializers
from .models import ScreeningCommittee
# from .serializers import UserBasicSerializer  # Assuming this is already defined

class ScreeningCommitteeSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()
    head_details = UserBasicSerializer(source='head', read_only=True)
    sub_head_details = UserBasicSerializer(source='sub_head', read_only=True)

    class Meta:
        model = ScreeningCommittee
        fields = [
            'id', 'service', 'name', 'committee_type', 'description',
            'head', 'head_details', 'sub_head', 'sub_head_details',
            'is_active', 'created_at', 'members_count', 'is_created'
        ]
        read_only_fields = ['created_at', 'is_created']

    def get_members_count(self, obj):
        return obj.members.filter(is_active=True).count()

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)







class ScreeningResultSerializer(serializers.ModelSerializer):
    committee_details = ScreeningCommitteeSerializer(source='committee', read_only=True)
    screener_details = UserBasicSerializer(source='screened_by', read_only=True)
    
    class Meta:
        model = ScreeningResult
        fields = [
            'id', 'application', 'committee', 'committee_details',
            'result', 'notes', 'screened_by', 'screener_details', 'screened_at'
        ]
        read_only_fields = ['screened_at']
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['screened_by'] = request.user
        
        if 'result' in validated_data and validated_data['result'] != 'pending' and not instance.screened_at:
            from django.utils import timezone
            validated_data['screened_at'] = timezone.now()
            
        return super().update(instance, validated_data)     

#  API 
# 
class CommitteeMemberWithHeadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    isHead = serializers.SerializerMethodField()

    class Meta:
        model = CommitteeMember
        fields = ('id', 'name', 'email', 'isHead')

    def get_name(self, obj):
        return getattr(obj.user, "get_full_name", lambda: None)() or getattr(obj.user, "full_name", None) or obj.user.email

    def get_isHead(self, obj):
        # head user is passed via context
        head_id = self.context.get('head_id')
        return obj.user.id == head_id if head_id else False    
       
    
class CommitteeSimpleSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    type = serializers.CharField(source='committee_type')

    class Meta:
        model = ScreeningCommittee
        fields = ['id', 'name', 'type', 'members']

    def get_members(self, obj):
        members = CommitteeMember.objects.filter(committee=obj, is_active=True).select_related('user')
        head_id = obj.head.id if obj.head else None
        # Pass head_id in context so serializer knows which is the head
        return CommitteeMemberWithHeadSerializer(members, many=True, context={'head_id': head_id}).data
    


