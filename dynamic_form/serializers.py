# dynamic_form/serializers.py

from rest_framework import serializers
from datetime import datetime
from .models import FormTemplate, FormSubmission

class FormSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmission
        fields = '__all__'
        read_only_fields = [
            'id','applicant','form_id','proposal_id',
            'created_at','updated_at'
        ]

    def validate(self, data):
        tpl = data.get('template') or self.instance.template
        now = datetime.now()
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
        if data.get('status') == FormSubmission.SUBMITTED:
            missing = []
            for req in self.context['request'].data.get('required_fields', []):
                if not self.context['request'].data.get(req):
                    missing.append(req)
            if missing:
                raise serializers.ValidationError(f"Missing required: {missing}")

        return data

    def create(self, validated_data):
        validated_data['applicant'] = self.context['request'].user
        return super().create(validated_data)


class FormTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FormTemplate
        fields = '__all__'


        