# dynamic_form/views.py

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from .models import FormTemplate, FormSubmission
from .serializers import FormSubmissionSerializer,FormTemplateSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework.decorators import action
import json
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
import json

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
    Create/Update/Delete Milestone objects for a FormSubmission, given a list of milestone dicts.
    """
    existing_milestones = {str(m.id): m for m in form_submission.milestones.all()}  # Use related_name or milestone_set if not set

    received_ids = set()
    for idx, m in enumerate(milestones_data):
        milestone_id = m.get("id")
        if milestone_id and str(milestone_id) in existing_milestones:
            # UPDATE existing milestone
            milestone = existing_milestones[str(milestone_id)]
            milestone.title = m.get("title") or milestone.title
            milestone.description = m.get("description") or milestone.description
            milestone.time_required = m.get("time_required") or milestone.time_required
            milestone.revised_time_required = m.get("revised_time_required") or milestone.revised_time_required
            milestone.grant_from_ttdf = m.get("grant_from_ttdf") or milestone.grant_from_ttdf
            milestone.initial_contri_applicant = m.get("initial_contri_applicant") or milestone.initial_contri_applicant
            milestone.revised_contri_applicant = m.get("revised_contri_applicant") or milestone.revised_contri_applicant
            milestone.initial_grant_from_ttdf = m.get("initial_grant_from_ttdf") or milestone.initial_grant_from_ttdf
            milestone.revised_grant_from_ttdf = m.get("revised_grant_from_ttdf") or milestone.revised_grant_from_ttdf
            milestone.save()
            received_ids.add(str(milestone_id))
        else:
            # CREATE new milestone
            new_milestone = Milestone.objects.create(
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
            received_ids.add(str(new_milestone.id))
    
    # Optionally DELETE milestones not present anymore (for PATCH, not for POST)
    to_delete = [m for mid, m in existing_milestones.items() if mid not in received_ids]
    for milestone in to_delete:
        milestone.delete()


# class FormSubmissionViewSet(viewsets.ModelViewSet): 
#     queryset = FormSubmission.objects.all().select_related('template', 'applicant')
#     serializer_class = FormSubmissionSerializer
#     permission_classes = [IsAuthenticated]
#     # authentication_classes = [JWTAuthentication]
#     lookup_field = 'pk'

#     def get_queryset(self):
#         return self.queryset.filter(applicant=self.request.user)

#     @transaction.atomic
#     def create(self, request, *args, **kwargs):
#         print("=== VIEW CREATE METHOD ===")
#         print(f"Request content type: {request.content_type}")
#         print(f"Request data keys: {list(request.data.keys())[:20]}")
        
#         # Check for nested array fields
#         nested_fields = ['collaborators', 'equipments', 'rdstaff', 'shareholders', 'iprdetails', 'sub_shareholders', 'fund_loan_documents']
#         for field in nested_fields:
#             indexed_keys = [key for key in request.data.keys() if key.startswith(f"{field}[")]
#             if indexed_keys:
#                 print(f"Found {len(indexed_keys)} indexed keys for {field}")
        
#         data = request.data.copy()
#         data.setdefault('status', FormSubmission.DRAFT)
        
#         upsert_profile_and_user_from_submission(request.user, data, files=request.FILES)

#         print("=== CREATING SERIALIZER ===")
#         serializer = self.get_serializer(data=data, context={'request': request})
        
#         print("=== VALIDATING SERIALIZER ===")
#         if serializer.is_valid():
#             print("✅ Serializer validation passed")
#             try:
#                 submission = serializer.save()
#                 print(f"✅ Submission created successfully: {submission.id}")
#             except Exception as save_exception:
#                 print(f"❌ Error during serializer.save(): {save_exception}")
#                 import traceback
#                 traceback.print_exc()
#                 return Response(
#                     {
#                         "success": False, 
#                         "message": f"Could not save submission: {str(save_exception)}", 
#                         "errors": {"save_error": str(save_exception)}
#                     },
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#         else:
#             print(f"❌ Serializer validation failed: {serializer.errors}")
#             return Response(
#                 {"success": False, "message": "Could not save submission.", "errors": serializer.errors},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Handle milestones
#         milestones = request.data.get("milestones")
#         if milestones and isinstance(milestones, list):
#             save_milestones_for_submission(submission, milestones, request.user)

#         msg = "Saved as draft." if serializer.data.get('status') == FormSubmission.DRAFT else "Submitted successfully."

#         # ---- THIS IS THE KEY PART ----
#         resp_data = serializer.data.copy()
#         resp_data['form_id'] = submission.form_id
#         # ---- END KEY PART ----

#         return Response(
#             {
#                 "success": True,
#                 "message": "Saved as draft." if submission.status == FormSubmission.DRAFT else "Submitted successfully.",
#                 "id": submission.id,
#                 "form_id": submission.form_id,
#                 "proposal_id": submission.proposal_id,
#                 "template": submission.template_id,
#                 "service": submission.service_id,
#                 "data": self.get_serializer(submission).data,
#             },
#             status=status.HTTP_201_CREATED
#         )

#     @transaction.atomic
#     def update(self, request, *args, **kwargs):
#         print("=== VIEW UPDATE METHOD ===")
        
#         partial = kwargs.pop('partial', False)
#         instance = self.get_object()
#         if instance.status != FormSubmission.DRAFT and request.data.get('status', instance.status) != FormSubmission.SUBMITTED:
#             return Response(
#                 {"success": False, "message": "Cannot edit a finalized submission."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#         data = request.data.copy()
#         upsert_profile_and_user_from_submission(request.user, data, files=request.FILES)

#         serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        
#         if serializer.is_valid():
#             print("✅ Serializer validation passed")
#             try:
#                 submission = serializer.save()
#                 print(f"✅ Submission updated successfully: {submission.id}")
#             except Exception as save_exception:
#                 print(f"❌ Error during serializer.save(): {save_exception}")
#                 import traceback
#                 traceback.print_exc()
#                 return Response(
#                     {
#                         "success": False, 
#                         "message": f"Could not update submission: {str(save_exception)}", 
#                         "errors": {"save_error": str(save_exception)}
#                     },
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#         else:
#             print(f"❌ Serializer validation failed: {serializer.errors}")
#             return Response(
#                 {"success": False, "message": "Could not update submission.", "errors": serializer.errors},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # Handle milestones
#         milestones = request.data.get("milestones")
#         if milestones and isinstance(milestones, list):
#             instance.milestones.all().delete()
#             save_milestones_for_submission(submission, milestones, request.user)

#         msg = "Saved as draft." if serializer.data.get('status') == FormSubmission.DRAFT else "Submitted successfully."
#         resp_data = serializer.data.copy()
#         resp_data['form_id'] = submission.form_id

#         return Response(
#             {
#                 "success": True,
#                 "message": "Saved as draft." if submission.status == FormSubmission.DRAFT else "Submitted successfully.",
#                 "data": self.get_serializer(submission).data,
#             },
#             status=status.HTTP_200_OK
#         )

#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         if instance.status != FormSubmission.DRAFT:
#             return Response(
#                 {"success": False, "message": "Only drafts can be deleted."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#         self.perform_destroy(instance)
#         return Response(
#             {"success": True, "message": "Draft deleted."},
#             status=status.HTTP_204_NO_CONTENT
#         )

#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         serializer = self.get_serializer(instance)
#         return Response(
#             {
#                 "success": True,
#                 "id": instance.id,
#                 "form_id": instance.form_id,
#                 "proposal_id": instance.proposal_id,
#                 "data": serializer.data
#             },
#             status=status.HTTP_200_OK
#         )

#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())
#         page = self.paginate_queryset(queryset)
#         serializer = self.get_serializer(page, many=True) if page is not None else self.get_serializer(queryset, many=True)
        
#         # Add "pk" to each item (same as "id") for frontend mapping
#         data_with_pk = []
#         for item in serializer.data:
#             item = dict(item)
#             item['pk'] = item['id']
#             data_with_pk.append(item)
        
#         if page is not None:
#             response = self.get_paginated_response(data_with_pk)
#             response.data["success"] = True
#             return response
#         else:
#             return Response(
#                 {"success": True, "data": data_with_pk},
#                 status=status.HTTP_200_OK
#             )
        



from rest_framework import status
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from rest_framework.serializers import ValidationError

class FormSubmissionViewSet(viewsets.ModelViewSet): 
    queryset = FormSubmission.objects.all().select_related('template', 'applicant')
    serializer_class = FormSubmissionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return self.queryset.filter(applicant=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            data.setdefault('status', FormSubmission.DRAFT)
            upsert_profile_and_user_from_submission(request.user, data, files=request.FILES)
            serializer = self.get_serializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            submission = serializer.save()
            # Optional: handle milestones if needed
            milestones = request.data.get("milestones")
            if milestones and isinstance(milestones, list):
                save_milestones_for_submission(submission, milestones, request.user)
            return Response(
                {
                    "success": True,
                    "message": "Saved as draft." if submission.status == FormSubmission.DRAFT else "Submitted successfully.",
                    "id": submission.id,
                    "form_id": submission.form_id,
                    "proposal_id": submission.proposal_id,
                    "template": submission.template_id,
                    "service": submission.service_id,
                    "data": self.get_serializer(submission).data,
                },
                status=status.HTTP_201_CREATED
            )
        except ValidationError as exc:
            # Clean field/non-field errors
            return Response(
                {
                    "success": False,
                    "message": "Could not save submission.",
                    "errors": exc.detail,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            # Unexpected error (debug log optional)
            import traceback; traceback.print_exc()
            return Response(
                {
                    "success": False,
                    "message": "An internal server error occurred.",
                    "errors": {"non_field_errors": [str(exc)]}
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != FormSubmission.DRAFT and request.data.get('status', instance.status) != FormSubmission.SUBMITTED:
            return Response(
                {"success": False, "message": "Cannot edit a finalized submission."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            data = request.data.copy()
            upsert_profile_and_user_from_submission(request.user, data, files=request.FILES)
            serializer = self.get_serializer(instance, data=data, partial=kwargs.get('partial', False), context={'request': request})
            serializer.is_valid(raise_exception=True)
            submission = serializer.save()
            # Optional: handle milestones if needed
            milestones = request.data.get("milestones")
            if milestones and isinstance(milestones, list):
                instance.milestones.all().delete()
                save_milestones_for_submission(submission, milestones, request.user)
            return Response(
                {
                    "success": True,
                    "message": "Saved as draft." if submission.status == FormSubmission.DRAFT else "Submitted successfully.",
                    "data": self.get_serializer(submission).data,
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as exc:
            return Response(
                {
                    "success": False,
                    "message": "Could not update submission.",
                    "errors": exc.detail,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            import traceback; traceback.print_exc()
            return Response(
                {
                    "success": False,
                    "message": "An internal server error occurred.",
                    "errors": {"non_field_errors": [str(exc)]}
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            {
                "success": True,
                "id": instance.id,
                "form_id": instance.form_id,
                "proposal_id": instance.proposal_id,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True) if page is not None else self.get_serializer(queryset, many=True)
        data_with_pk = []
        for item in serializer.data:
            item = dict(item)
            item['pk'] = item['id']
            data_with_pk.append(item)
        if page is not None:
            response = self.get_paginated_response(data_with_pk)
            response.data["success"] = True
            return response
        else:
            return Response(
                {"success": True, "data": data_with_pk},
                status=status.HTTP_200_OK
            )



from rest_framework.views import APIView
from rest_framework.response import Response
from collections import defaultdict
from .models import FormSubmission

class ProposalVillageStatsAPIView(APIView):
    """
    API to get:
        - total_proposals
        - per_village stats (village code, label, count, proposals with id/service/template)
    """
    def get(self, request):
        # Only proposals where proposed_village is set
        queryset = (
            FormSubmission.objects
            .filter(is_active=True)
            .exclude(status=FormSubmission.DRAFT)
            .exclude(proposed_village__isnull=True)
            .exclude(proposed_village__exact="")
        )

        total_proposals = queryset.count()

        # Get the display names for village choices
        village_field = FormSubmission._meta.get_field('proposed_village')
        village_map = dict(village_field.choices)

        # Collect proposals per village code
        per_village_data = defaultdict(list)
        for proposal in queryset:
            per_village_data[proposal.proposed_village].append(proposal)

        results = []
        for village_code, proposals in per_village_data.items():
            display_name = village_map.get(village_code, village_code) or "Unknown"
            results.append({
                "village": village_code,
                "village_display": display_name,
                "count": len(proposals),
                "proposals": [
                    {
                        "proposal_id": p.proposal_id,
                        "service_name": getattr(p.service, "name", ""),
                        "template_title": getattr(p.template, "title", ""),
                        "status": p.status,
                    } for p in proposals
                ]
            })

        results = sorted(results, key=lambda x: x['village_display'] or "")

        return Response({
            "total_proposals": total_proposals,
            "per_village": results,
        })
