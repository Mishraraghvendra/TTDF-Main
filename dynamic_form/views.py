# dynamic_form/views.py

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import FormTemplate, FormSubmission
from .serializers import FormSubmissionSerializer,FormTemplateSerializer
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from dynamic_form.models import FormSubmission
from screening.serializers import (
    ScreeningRecordSerializer,
    TechnicalScreeningRecordSerializer
)

from datetime import datetime
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import FormSubmission
from .serializers import FormSubmissionSerializer
from screening.serializers import ScreeningRecordSerializer, TechnicalScreeningRecordSerializer

# Committee‐head lives in the configuration app
from configuration.models import ScreeningCommittee



class FormTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin can list/create templates; applicants only list active ones.
    """
    queryset = FormTemplate.objects.all()
    serializer_class = FormTemplateSerializer 
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_staff:
            qs = qs.filter(is_active=True, start_date__lte=datetime.now(), end_date__gte=datetime.now())
        return qs



class FormSubmissionViewSet(viewsets.ModelViewSet):
    """
    Applicants manage their own submissions.
    Committee‐heads can record admin & tech screening and finalize.
    """
    queryset         = FormSubmission.objects.all().select_related('template','applicant')
    serializer_class = FormSubmissionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field     = 'form_id'

    def get_queryset(self):
        # Only show the current user's submissions
        return self.queryset.filter(applicant=self.request.user)

    def _is_committee_head(self, user):
        # True if user is head or sub_head on any ScreeningCommittee
        return ScreeningCommittee.objects.filter(
            Q(head=user) | Q(sub_head=user)
        ).exists()

    @action(detail=True, methods=['post'], url_path='admin-screen')
    def admin_screen(self, request, form_id=None):
        submission = self.get_object()
        if not self._is_committee_head(request.user):
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        # Build payload for ScreeningRecord
        payload = {'submission': submission.id}
        if 'document' in request.data:
            payload['document'] = request.data['document']

        sr = ScreeningRecordSerializer(data=payload, context={'request': request})
        sr.is_valid(raise_exception=True)
        # Save with the user who screened it
        sr.save(screened_by=request.user)

        # Update proposal status
        submission.status = FormSubmission.EVALUATED
        submission.save(update_fields=['status'])

        return Response({'detail': 'Admin screening recorded.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='tech-screen')
    def tech_screen(self, request, form_id=None):
        submission = self.get_object()
        if not self._is_committee_head(request.user):
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        payload = {'submission': submission.id}
        if 'document' in request.data:
            payload['document'] = request.data['document']

        ts = TechnicalScreeningRecordSerializer(data=payload, context={'request': request})
        ts.is_valid(raise_exception=True)
        ts.save(screened_by=request.user)

        submission.status = FormSubmission.TECHNICAL
        submission.save(update_fields=['status'])

        return Response({'detail': 'Technical screening recorded.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='finalize')
    def finalize(self, request, form_id=None):
        submission = self.get_object()
        if not self._is_committee_head(request.user):
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        verdict = request.data.get('verdict', '').lower()
        if verdict not in ('approve', 'reject'):
            return Response(
                {'detail': "Invalid verdict; must be 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        submission.status = (
            FormSubmission.APPROVED if verdict == 'approve'
            else FormSubmission.REJECTED
        )
        submission.save(update_fields=['status'])

        return Response({'detail': 'Proposal finalized.'}, status=status.HTTP_200_OK)
