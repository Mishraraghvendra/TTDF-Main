# dynamic_form/views.py

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from .models import FormTemplate, FormSubmission
from .serializers import FormSubmissionSerializer,FormTemplateSerializer

from rest_framework.decorators import action

from screening.serializers import (
    ScreeningRecordSerializer,
    TechnicalScreeningRecordSerializer
)

from datetime import datetime
from django.db.models import Q
from django.db import transaction

# Committee‐head lives in the configuration app
from configuration.models import ScreeningCommittee
from milestones.models import Milestone
from users.utils import upsert_profile_and_user_from_submission


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



def save_milestones_for_submission(form_submission, milestones_data, user=None):
    """
    Create Milestone objects for a FormSubmission, given a list of milestone dicts.
    """
    for idx, m in enumerate(milestones_data):
        Milestone.objects.create(
            proposal=form_submission,
            title=m.get("title") or f"Milestone {idx+1}",
            description=m.get("description") or "",
            time_required=m.get("time_required") or 0,
            revised_time_required=m.get("revised_time_required"),
            grant_from_ttdf=m.get("grant_from_ttdf") or 0,
            initial_contri_applicant=m.get("initial_contri_applicant") or 0,
            revised_contri_applicant=m.get("revised_contri_applicant"),
            initial_grant_from_ttdf=m.get("initial_grant_from_ttdf"),
            revised_grant_from_ttdf=m.get("revised_grant_from_ttdf"),
            created_by=user,
        )

class FormSubmissionViewSet(viewsets.ModelViewSet): 
    queryset = FormSubmission.objects.all().select_related('template', 'applicant')
    serializer_class = FormSubmissionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return self.queryset.filter(applicant=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data.setdefault('status', FormSubmission.DRAFT)

        # --- Update/create user and profile data
        upsert_profile_and_user_from_submission(request.user, data, files=request.FILES)

        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
            submission = serializer.save()
        except Exception:
            return Response(
                {"success": False, "message": "Could not save submission.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Save milestones if provided
        milestones = request.data.get("milestones")
        if milestones and isinstance(milestones, list):
            save_milestones_for_submission(submission, milestones, request.user)

        msg = "Saved as draft." if serializer.data.get('status') == FormSubmission.DRAFT else "Submitted successfully."
        return Response(
            {"success": True, "message": msg, "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if instance.status != FormSubmission.DRAFT and request.data.get('status', instance.status) != FormSubmission.SUBMITTED:
            return Response(
                {"success": False, "message": "Cannot edit a finalized submission."},
                status=status.HTTP_400_BAD_REQUEST
            )
        data = request.data.copy()

        # --- Update/create user and profile data
        upsert_profile_and_user_from_submission(request.user, data, files=request.FILES)

        serializer = self.get_serializer(instance, data=data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
            submission = serializer.save()
        except Exception:
            return Response(
                {"success": False, "message": "Could not update submission.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        milestones = request.data.get("milestones")
        if milestones and isinstance(milestones, list):
            instance.milestones.all().delete()
            save_milestones_for_submission(submission, milestones, request.user)

        msg = "Saved as draft." if serializer.data.get('status') == FormSubmission.DRAFT else "Submitted successfully."
        return Response(
            {"success": True, "message": msg, "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != FormSubmission.DRAFT:
            return Response(
                {"success": False, "message": "Only drafts can be deleted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        self.perform_destroy(instance)
        return Response(
            {"success": True, "message": "Draft deleted."},
            status=status.HTTP_204_NO_CONTENT
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True) if page is not None else self.get_serializer(queryset, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK
        )