from rest_framework import serializers
from .models import ActivityLog

class ActivityLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    user_name = serializers.CharField(source='user.get_full_name', read_only=True, default="")
    last_login = serializers.DateTimeField(source='user.last_login', read_only=True, default=None)
    class Meta:
        model = ActivityLog
        fields = '__all__'

    # class Meta:
    #     model = ActivityLog
    #     fields = '__all__'



# serializers.py

from django.contrib.auth import get_user_model
from rest_framework import serializers
from audit.models import ActivityLog

User = get_user_model()

class UserAuditSerializer(serializers.ModelSerializer):
    last_login = serializers.DateTimeField()
    email = serializers.EmailField()
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'last_login']
