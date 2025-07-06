# dynamic_form/serializers.py

from rest_framework import serializers

from .models import FormTemplate, FormSubmission
from milestones.serializers import MilestoneSerializer
from users.serializers import ProfileSerializer  # adjust import as per your app
from users.models import User, Profile
from django.utils import timezone


class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "gender", "mobile", "email", "organization"]

class FullProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        exclude = ["id", "user"]

class FormSubmissionSerializer(serializers.ModelSerializer):    
    
    class Meta:
        model = FormSubmission
        fields = '__all__'
        read_only_fields = [
            'id','applicant','form_id','proposal_id',
            'created_at','updated_at'
        ] + ['service_name', 'last_updated','create_date']

    milestones = MilestoneSerializer(many=True, read_only=True)
    applicant = UserShortSerializer(read_only=True)
    profile = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()
    last_updated = serializers.SerializerMethodField()
    create_date = serializers.SerializerMethodField()


    def get_service_name(self, obj):
        return obj.service.name if obj.service else None

    def get_last_updated(self, obj):
        if obj.updated_at:
            return timezone.localtime(obj.updated_at).strftime('%Y-%m-%d %H:%M:%S')
        return None

    def get_create_date(self, obj):
        if obj.created_at:
            return timezone.localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
        return None

    def get_profile(self, obj):
        # Get Profile for this applicant (User)
        profile = getattr(obj.applicant, "profile", None)
        if not profile:
            return None
        return FullProfileSerializer(profile).data

    
    def validate(self, data):
        tpl = data.get('template') or self.instance.template
        now = timezone.now()   # <--- always use this!
    # enforce template window
        if not tpl.is_active:
            raise serializers.ValidationError("Form not active.")
        if tpl.start_date and now < tpl.start_date:
            raise serializers.ValidationError("Not open yet.")
        if tpl.end_date and now > tpl.end_date:
            raise serializers.ValidationError("Deadline passed.")

        # check edit permission
        if self.instance and not self.instance.can_edit():
            raise serializers.ValidationError("Cannot edit after deadline/final submit.")

        # on submit, ensure required frontend‐defined fields are present

        # if data.get('status') == FormSubmission.SUBMITTED:
        #     missing = []
        #     for req in self.context['request'].data.get('required_fields', []):
        #         if not self.context['request'].data.get(req):
        #             missing.append(req)
        #     if missing:
        #         raise serializers.ValidationError(f"Missing required: {missing}")

        return data

    def create(self, validated_data):
        validated_data['applicant'] = self.context['request'].user
        return super().create(validated_data)


class FormTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FormTemplate
        fields = '__all__'


        