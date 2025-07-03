from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import StaticForm
from .serializers import StaticFormSerializer

class StaticFormViewSet(viewsets.ModelViewSet):
    serializer_class = StaticFormSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return StaticForm.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.data.get("final_submit", False) and instance.status == 'draft':
            instance.generate_and_save_proposal_id()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        return super().update(request, *args, **kwargs)
