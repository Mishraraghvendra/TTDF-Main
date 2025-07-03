from rest_framework import serializers
from .models import StaticForm

class StaticFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticForm
        fields = '__all__'
        read_only_fields = ['user', 'form_id', 'proposal_id', 'status', 'created_at', 'updated_at']
