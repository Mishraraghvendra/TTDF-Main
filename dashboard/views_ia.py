from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import (
    Count, Q, Sum, Max, F, Value, CharField, DecimalField, Case, When
)


from dynamic_form.models import FormSubmission
from milestones.models import Milestone, SubMilestone, PaymentClaim, FinanceRequest


from rest_framework.permissions import IsAuthenticated
from configuration.models import Service
from milestones.models import MilestoneDocument
from presentation.models import Presentation

class IADashboardAPIView(APIView):
    """
    Fast IA Dashboard API with summary and per-proposal breakdown.
    """

    def get(self, request, *args, **kwargs):
        # --- Summary Cards ---
        total_proposals = FormSubmission.objects.filter(is_active=True).count()
        mou_signed = FormSubmission.objects.filter(
            is_active=True, mou_document__isnull=False
        ).count()
        mou_pending = total_proposals - mou_signed
        shortlisted = FormSubmission.objects.filter(
            is_active=True, status=FormSubmission.APPROVED
        ).count()

        # --- Financial Aggregates ---
        # Total, utilized, unutilized from milestones (all proposals)
        fin = Milestone.objects.aggregate(
            total_requirement=Sum(F('grant_from_ttdf') + F('revised_grant_from_ttdf')),
            total_expenditure=Sum('funds_requested')
        )
        total_requirement = fin['total_requirement'] or 0
        total_expenditure = fin['total_expenditure'] or 0
        utilization = total_expenditure  # or your actual utilization logic
        unutilized = (total_requirement or 0) - (total_expenditure or 0)

        # --- Proposal Breakdown ---
        proposals = (
            FormSubmission.objects.filter(is_active=True)
            .select_related('service', 'applicant')
            .prefetch_related(
                'milestones__submilestones',
                'milestones__documents',
                'milestones__payment_claims',
                'milestones__finance_requests'
            )
            .order_by('-created_at')
        )

        proposal_data = []
        for proposal in proposals:
            # Get latest milestone (by updated_at)
            latest_ms = proposal.milestones.order_by('-updated_at').first()
            latest_subms = (
                latest_ms.submilestones.order_by('-updated_at').first()
                if latest_ms else None
            )

            # Latest Payment Claim
            latest_claim = (
                latest_ms.payment_claims.order_by('-created_at').first()
                if latest_ms else None
            )
            # Latest Finance Request
            latest_fin_req = (
                latest_ms.finance_requests.order_by('-created_at').first()
                if latest_ms else None
            )

            # Milestone status counts for this proposal
            milestone_counts = proposal.milestones.values('status').annotate(cnt=Count('id'))
            ms_status_map = {row['status']: row['cnt'] for row in milestone_counts}

            proposal_data.append({
                "proposal_id": proposal.proposal_id,
                "service": proposal.service.name if proposal.service else None,
                "subject": proposal.subject,
                "org_type": proposal.org_type,
                "org_name": getattr(proposal.applicant, 'organization', None),
                "status": proposal.status,
                "created_at": proposal.created_at,
                # Milestones & submilestones
                "latest_milestone": {
                    "title": latest_ms.title if latest_ms else None,
                    "status": latest_ms.status if latest_ms else None,
                    "due_date": latest_ms.due_date if latest_ms else None,
                    "updated_at": latest_ms.updated_at if latest_ms else None,
                } if latest_ms else None,
                "latest_submilestone": {
                    "title": latest_subms.title if latest_subms else None,
                    "status": latest_subms.status if latest_subms else None,
                    "due_date": latest_subms.due_date if latest_subms else None,
                    "updated_at": latest_subms.updated_at if latest_subms else None,
                } if latest_subms else None,
                # Finance/claim summary
                "latest_payment_claim": {
                    "amount": latest_claim.net_claim_amount if latest_claim else None,
                    "status": latest_claim.status if latest_claim else None,
                    "created_at": latest_claim.created_at if latest_claim else None,
                } if latest_claim else None,
                "latest_finance_request": {
                    "status": latest_fin_req.status if latest_fin_req else None,
                    "created_at": latest_fin_req.created_at if latest_fin_req else None,
                } if latest_fin_req else None,
                "milestone_status_counts": ms_status_map,
            })

        # --- Response ---
        return Response({
            "summary": {
                "total_proposals": total_proposals,
                "mou_signed": mou_signed,
                "mou_pending": mou_pending,
                "shortlisted": shortlisted,
                "total_requirement": total_requirement,
                "utilization": utilization,
                "unutilized": unutilized,
            },
            "proposals": proposal_data,
        })


class AllServicesAPIView(APIView):
    """
    Returns all services and their details.
    """
    def get(self, request, *args, **kwargs):
        # Fetch all services, only required fields for speed
        services = Service.objects.all()
        results = []
        for svc in services:
            results.append({
                "id": svc.id,
                "name": svc.name,
                "description": getattr(svc, 'description', ''),   # skip if not present
                # add more fields as needed!
                # "some_field": svc.some_field,
            })
        return Response(results)

from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import models
from configuration.models import Service
from milestones.models import Milestone, MilestoneDocument
from collections import defaultdict

class DocumentStatusCountAPIView(APIView):
    """
    For each service and overall, counts MPR/MCR/UC/Asset documents per status and gives a total per type.
    """
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        results = []
        # For global totals
        total_counts = {
            'mpr': defaultdict(int),
            'mcr': defaultdict(int),
            'uc': defaultdict(int),
            'assets': defaultdict(int),
        }
        # For global total per type
        global_type_totals = defaultdict(int)

        for service in services:
            milestones = Milestone.objects.filter(proposal__service=service)
            docs = MilestoneDocument.objects.filter(milestone__in=milestones)
            counts = {}
            # For total per doc type (for this service)
            type_totals = {}
            for doc_type, status_field in [
                ('mpr', 'mpr_status'),
                ('mcr', 'mcr_status'),
                ('uc', 'uc_status'),
                ('assets', 'assets_status'),
            ]:
                status_counts = docs.values(status_field).order_by().annotate(count=models.Count('id'))
                status_result = {}
                doc_type_total = 0
                for row in status_counts:
                    status = row[status_field]
                    count = row['count']
                    status_result[status] = count
                    doc_type_total += count
                    total_counts[doc_type][status] += count
                    global_type_totals[doc_type] += count
                status_result['total'] = doc_type_total
                counts[doc_type] = status_result
            results.append({
                "service_id": service.id,
                "service_name": service.name,
                "document_status_counts": counts,
            })
        # Prepare combined with totals per type
        combined = {}
        for doc_type, status_counts in total_counts.items():
            out = dict(status_counts)
            out['total'] = global_type_totals[doc_type]
            combined[doc_type] = out
        return Response({
            "services": results,
            "combined": combined
        })


class IASummaryAPIView(APIView):
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        service_data = []
        overall_total_proposals = overall_mou_signed = overall_shortlisted = 0

        for service in services:
            proposals = FormSubmission.objects.filter(is_active=True, service=service)
            proposal_ids = list(proposals.values_list('id', flat=True))

            # MOU signed (has related ProposalMouDocument)
            mou_signed = proposals.filter(mou_document__isnull=False).count()
            total_proposals = proposals.count()
            mou_pending = total_proposals - mou_signed

            # Presentations shortlisted for this service's proposals
            shortlisted = Presentation.objects.filter(
                proposal__in=proposals, final_decision="shortlisted"
            ).count()

            # Update overall counters
            overall_total_proposals += total_proposals
            overall_mou_signed += mou_signed
            overall_shortlisted += shortlisted

            service_data.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "total_proposals": total_proposals,
                "mou_signed": mou_signed,
                "mou_pending": mou_pending,
                "shortlisted": shortlisted,
            })

        overall_mou_pending = overall_total_proposals - overall_mou_signed

        return Response({
            "total_proposals": overall_total_proposals,
            "mou_signed": overall_mou_signed,
            "mou_pending": overall_mou_pending,
            "shortlisted": overall_shortlisted,
            "services": service_data
        })
    

class IAUtilizationOverviewAPIView(APIView):
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        overall_total_requirement = 0
        overall_total_expenditure = 0

        service_data = []

        for service in services:
            milestones = Milestone.objects.filter(proposal__service=service)
            # Calculate sums for this service
            agg = milestones.aggregate(
                total_requirement=Sum(F('grant_from_ttdf') + F('revised_grant_from_ttdf')),
                total_expenditure=Sum('funds_requested')
            )
            total_requirement = agg['total_requirement'] or 0
            total_expenditure = agg['total_expenditure'] or 0
            utilization = total_expenditure
            unutilized = total_requirement - total_expenditure

            overall_total_requirement += total_requirement
            overall_total_expenditure += total_expenditure

            service_data.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "total_requirement": total_requirement,
                "utilization": utilization,
                "unutilized": unutilized,
            })

        overall_unutilized = overall_total_requirement - overall_total_expenditure

        return Response({
            "total_requirement": overall_total_requirement,
            "utilization": overall_total_expenditure,
            "unutilized": overall_unutilized,
            "services": service_data
        })


from rest_framework.pagination import PageNumberPagination

class ProposalTrackerPagination(PageNumberPagination):
    page_size = 20

class IAProposalTrackerAPIView(APIView):
    def get(self, request, *args, **kwargs):
        proposals = (
            FormSubmission.objects.filter(is_active=True)
            .select_related('service', 'applicant')
            .prefetch_related('milestones__submilestones', 'milestones__documents', 'milestones__payment_claims', 'milestones__finance_requests')
            .order_by('-created_at')
        )
        paginator = ProposalTrackerPagination()
        page = paginator.paginate_queryset(proposals, request)
        result = []
        for proposal in page:
            latest_ms = proposal.milestones.order_by('-updated_at').first()
            latest_subms = latest_ms.submilestones.order_by('-updated_at').first() if latest_ms else None
            latest_claim = latest_ms.payment_claims.order_by('-created_at').first() if latest_ms else None
            latest_fin_req = latest_ms.finance_requests.order_by('-created_at').first() if latest_ms else None
            result.append({
                "proposal_id": proposal.proposal_id,
                "service": proposal.service.name if proposal.service else None,
                "subject": proposal.subject,
                "org_type": proposal.org_type,
                "org_name": getattr(proposal.applicant, 'organization', None),
                "status": proposal.status,
                "created_at": proposal.created_at,
                "latest_milestone": {
                    "title": latest_ms.title if latest_ms else None,
                    "status": latest_ms.status if latest_ms else None,
                    "due_date": latest_ms.due_date if latest_ms else None,
                    "updated_at": latest_ms.updated_at if latest_ms else None,
                } if latest_ms else None,
                "latest_submilestone": {
                    "title": latest_subms.title if latest_subms else None,
                    "status": latest_subms.status if latest_subms else None,
                    "due_date": latest_subms.due_date if latest_subms else None,
                    "updated_at": latest_subms.updated_at if latest_subms else None,
                } if latest_subms else None,
                "latest_payment_claim": {
                    "amount": latest_claim.net_claim_amount if latest_claim else None,
                    "status": latest_claim.status if latest_claim else None,
                    "created_at": latest_claim.created_at if latest_claim else None,
                } if latest_claim else None,
                "latest_finance_request": {
                    "status": latest_fin_req.status if latest_fin_req else None,
                    "created_at": latest_fin_req.created_at if latest_fin_req else None,
                } if latest_fin_req else None,
            })
        return paginator.get_paginated_response(result)


class IAMilestoneStatusAPIView(APIView):
    def get(self, request, *args, **kwargs):
        ms_counts = (
            Milestone.objects.values('status')
            .annotate(count=Count('id')).order_by('status')
        )
        subms_counts = (
            SubMilestone.objects.values('status')
            .annotate(count=Count('id')).order_by('status')
        )
        return Response({
            "milestone_status_counts": {row['status']: row['count'] for row in ms_counts},
            "submilestone_status_counts": {row['status']: row['count'] for row in subms_counts},
        })


from rest_framework.pagination import PageNumberPagination

class SimplePagination(PageNumberPagination):
    page_size = 20


# class IAProposalFinancialStatusAPIView(APIView):
#     def get(self, request, *args, **kwargs):
#         proposal_id = request.query_params.get("proposal_id")
#         proposals = FormSubmission.objects.filter(is_active=True)
#         if proposal_id:
#             proposals = proposals.filter(proposal_id=proposal_id)
#             if not proposals.exists():
#                 return Response({"error": f"Proposal {proposal_id} not found"}, status=404)

#         # Pagination for all proposals
#         paginator = SimplePagination()
#         page = paginator.paginate_queryset(proposals, request)
#         proposal_ids = [p.proposal_id for p in page]

#         # Use correct lookup: proposal__proposal_id__in
#         milestones = Milestone.objects.filter(proposal__proposal_id__in=proposal_ids)
#         milestone_map = {ms.proposal.proposal_id: [] for ms in milestones}
#         for ms in milestones:
#             milestone_map.setdefault(ms.proposal.proposal_id, []).append(ms.id)

#         # Bulk milestone docs (by milestone__in)
#         docs = MilestoneDocument.objects.filter(milestone__in=milestones)
#         doc_map = {}
#         for doc in docs:
#             doc_map.setdefault(doc.milestone.proposal.proposal_id, []).append(doc)

#         # Bulk latest claims (by proposal__proposal_id__in)
#         claims = PaymentClaim.objects.filter(proposal__proposal_id__in=proposal_ids).order_by('proposal', '-created_at')
#         claim_map = {}
#         for claim in claims:
#             # claim.proposal.proposal_id is the business ID string
#             pid = claim.proposal.proposal_id
#             if pid not in claim_map:
#                 claim_map[pid] = claim

#         results = []
#         for proposal in page:
#             ms_ids = milestone_map.get(proposal.proposal_id, [])
#             ms_docs = [d for d in docs if d.milestone.proposal.proposal_id == proposal.proposal_id]
#             uc_approved = sum(1 for d in ms_docs if d.uc_status == 'accepted')
#             mpr_approved = sum(1 for d in ms_docs if d.mpr_status == 'accepted')
#             mcr_approved = sum(1 for d in ms_docs if d.mcr_status == 'accepted')
#             assets_purchased = sum(1 for d in ms_docs if d.assets_status == 'accepted')
#             latest_claim = claim_map.get(proposal.proposal_id)

#             cap_requirement = Milestone.objects.filter(proposal__proposal_id=proposal.proposal_id).aggregate(
#                 total=Sum(F('grant_from_ttdf') + F('revised_grant_from_ttdf'))
#             )['total'] or 0
#             cap_expenditure = Milestone.objects.filter(proposal__proposal_id=proposal.proposal_id).aggregate(
#                 total=Sum('funds_requested')
#             )['total'] or 0

#             results.append({
#                 "proposal_id": proposal.proposal_id,
#                 "capital_requirement": cap_requirement,
#                 "capital_expenditure": cap_expenditure,
#                 "uc_approved": uc_approved,
#                 "mpr_approved": mpr_approved,
#                 "mcr_approved": mcr_approved,
#                 "assets_purchased": assets_purchased,
#                 "latest_claim": {
#                     "amount": latest_claim.net_claim_amount if latest_claim else None,
#                     "status": latest_claim.status if latest_claim else None,
#                     "created_at": latest_claim.created_at if latest_claim else None,
#                 } if latest_claim else None,
#             })
#         return paginator.get_paginated_response(results)

class IAProposalFinancialStatusAPIView(APIView):
    def get(self, request, *args, **kwargs):
        proposal_id = request.query_params.get("proposal_id")
        proposals = FormSubmission.objects.filter(is_active=True)
        if proposal_id:
            proposals = proposals.filter(proposal_id=proposal_id)
            if not proposals.exists():
                return Response({"error": f"Proposal {proposal_id} not found"}, status=404)

        paginator = SimplePagination()
        page = paginator.paginate_queryset(proposals, request)
        proposal_ids = [p.proposal_id for p in page]

        # Prefetch milestones for all proposals in page
        milestones = Milestone.objects.filter(proposal__proposal_id__in=proposal_ids)
        # Map milestones by proposal.proposal_id
        milestone_map = {}
        for ms in milestones:
            milestone_map.setdefault(ms.proposal.proposal_id, []).append(ms)

        # Bulk milestone docs
        docs = MilestoneDocument.objects.filter(milestone__in=milestones)
        doc_map = {}
        for doc in docs:
            pid = doc.milestone.proposal.proposal_id
            doc_map.setdefault(pid, []).append(doc)

        # Bulk latest claims
        claims = PaymentClaim.objects.filter(proposal__proposal_id__in=proposal_ids).order_by('proposal', '-created_at')
        claim_map = {}
        for claim in claims:
            pid = claim.proposal.proposal_id
            if pid not in claim_map:
                claim_map[pid] = claim

        # Group proposals by service name
        service_map = {}
        for proposal in page:
            ms_list = milestone_map.get(proposal.proposal_id, [])
            ms_docs = doc_map.get(proposal.proposal_id, [])
            uc_approved = sum(1 for d in ms_docs if d.uc_status == 'accepted')
            mpr_approved = sum(1 for d in ms_docs if d.mpr_status == 'accepted')
            mcr_approved = sum(1 for d in ms_docs if d.mcr_status == 'accepted')
            assets_purchased = sum(1 for d in ms_docs if d.assets_status == 'accepted')
            latest_claim = claim_map.get(proposal.proposal_id)

            # Aggregate cap_requirement and cap_expenditure for all milestones of this proposal
            cap_requirement = sum(
                (ms.grant_from_ttdf or 0) + (ms.revised_grant_from_ttdf or 0) for ms in ms_list
            )
            cap_expenditure = sum(ms.funds_requested or 0 for ms in ms_list)

            service_name = proposal.service.name if proposal.service else "Unknown"

            proposal_fin_status = {
                "proposal_id": proposal.proposal_id,
                "capital_requirement": cap_requirement,
                "capital_expenditure": cap_expenditure,
                "uc_approved": uc_approved,
                "mpr_approved": mpr_approved,
                "mcr_approved": mcr_approved,
                "assets_purchased": assets_purchased,
                "latest_claim": {
                    "amount": latest_claim.net_claim_amount if latest_claim else None,
                    "status": latest_claim.status if latest_claim else None,
                    "created_at": latest_claim.created_at if latest_claim else None,
                } if latest_claim else None,
            }
            service_map.setdefault(service_name, []).append(proposal_fin_status)

        # If single proposal and only one service, return that
        if proposal_id and len(service_map) == 1:
            # Return only the list for the matching service
            return Response(next(iter(service_map.values()))[0])

        return paginator.get_paginated_response(service_map)












class IAServiceWiseDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        proposals = FormSubmission.objects.filter(is_active=True)
        milestones = Milestone.objects.select_related('proposal__service')
        claims = PaymentClaim.objects.filter(status=PaymentClaim.JF_APPROVED)

        service_data = []

        for service in services:
            service_proposals = proposals.filter(service=service)
            service_milestones = milestones.filter(proposal__service=service)

            total_requirement = service_milestones.aggregate(
                total=Sum('grant_from_ttdf')
            )['total'] or 0

            utilization = claims.filter(
                milestone__proposal__service=service
            ).aggregate(total=Sum('net_claim_amount'))['total'] or 0

            unutilized = total_requirement - utilization

            # Proposal/milestone counts
            ms_status_counts = service_milestones.values('status').annotate(count=Count('id'))
            milestone_status = {row['status']: row['count'] for row in ms_status_counts}

            service_data.append({
                "service_id": service.id,
                "service_name": service.name,
                "status": service.status,
                "total_proposals": service_proposals.count(),
                "approved_proposals": service_proposals.filter(status=FormSubmission.APPROVED).count(),
                "mou_signed": service_proposals.filter(mou_document__isnull=False).count(),
                "mou_pending": service_proposals.filter(mou_document__isnull=True).count(),
                "total_requirement": total_requirement,
                "utilization": utilization,
                "unutilized": unutilized,
                "milestone_status_counts": milestone_status,
            })

        return Response({
            "services_summary": service_data,
            "totals": {
                "total_services": services.count(),
                "active_services": services.filter(status='active').count(),
                "draft_services": services.filter(status='draft').count(),
                "total_proposals": proposals.count(),
                "approved_proposals": proposals.filter(status=FormSubmission.APPROVED).count(),
                "mou_signed": proposals.filter(mou_document__isnull=False).count(),
                "mou_pending": proposals.filter(mou_document__isnull=True).count(),
                "total_requirement": milestones.aggregate(total=Sum('grant_from_ttdf'))['total'] or 0,
                "utilization": claims.aggregate(total=Sum('net_claim_amount'))['total'] or 0,
            }
        })


class IAServiceSummaryAPIView(APIView):
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        result = []
        for service in services:
            proposals = FormSubmission.objects.filter(is_active=True, service=service)
            total_proposals = proposals.count()
            mou_signed = proposals.filter(mou_document__isnull=False).count()
            shortlisted = proposals.filter(status=FormSubmission.APPROVED).count()
            result.append({
                "service_id": service.id,
                "service_name": service.name,
                "total_proposals": total_proposals,
                "mou_signed": mou_signed,
                "mou_pending": total_proposals - mou_signed,
                "shortlisted": shortlisted
            })
        return Response(result)
    
class IAServiceUtilizationAPIView(APIView):
    def get(self, request, *args, **kwargs):
        from configuration.models import Service
        services = Service.objects.all()
        result = []
        for service in services:
            milestones = Milestone.objects.filter(proposal__service=service)
            total_requirement = milestones.aggregate(
                total=Sum('grant_from_ttdf')
            )['total'] or 0
            utilization = PaymentClaim.objects.filter(
                milestone__proposal__service=service,
                status=PaymentClaim.JF_APPROVED
            ).aggregate(total=Sum('net_claim_amount'))['total'] or 0
            unutilized = total_requirement - utilization
            result.append({
                "service_id": service.id,
                "service_name": service.name,
                "total_requirement": total_requirement,
                "utilization": utilization,
                "unutilized": unutilized,
            })
        return Response(result)

        
class IAServiceProposalsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        from configuration.models import Service
        services = Service.objects.all()
        result = []
        for service in services:
            proposals = FormSubmission.objects.filter(is_active=True, service=service)
            for proposal in proposals:
                result.append({
                    "service_id": service.id,
                    "service_name": service.name,
                    "proposal_id": proposal.proposal_id,
                    "subject": proposal.subject,
                    "org_type": proposal.org_type,
                    "org_name": getattr(proposal.applicant, 'organization', None),
                    "status": proposal.status,
                    "created_at": proposal.created_at,
                })
        return Response(result)
    

class IAServiceMilestoneClaimsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        from configuration.models import Service
        services = Service.objects.all()
        data = []
        for service in services:
            milestones = Milestone.objects.filter(proposal__service=service)
            for ms in milestones:
                latest_subms = ms.submilestones.order_by('-updated_at').first()
                latest_claim = ms.payment_claims.order_by('-created_at').first()
                latest_fin_req = ms.finance_requests.order_by('-created_at').first()
                milestone_counts = ms.proposal.milestones.values('status').annotate(cnt=Count('id'))
                ms_status_map = {row['status']: row['cnt'] for row in milestone_counts}
                data.append({
                    "service_id": service.id,
                    "service_name": service.name,
                    "proposal_id": ms.proposal.proposal_id,
                    "milestone_title": ms.title,
                    "milestone_status": ms.status,
                    "milestone_due_date": ms.due_date,
                    "latest_submilestone": {
                        "title": latest_subms.title if latest_subms else None,
                        "status": latest_subms.status if latest_subms else None,
                        "due_date": latest_subms.due_date if latest_subms else None,
                        "updated_at": latest_subms.updated_at if latest_subms else None,
                    } if latest_subms else None,
                    "latest_payment_claim": {
                        "amount": latest_claim.net_claim_amount if latest_claim else None,
                        "status": latest_claim.status if latest_claim else None,
                        "created_at": latest_claim.created_at if latest_claim else None,
                    } if latest_claim else None,
                    "latest_finance_request": {
                        "status": latest_fin_req.status if latest_fin_req else None,
                        "created_at": latest_fin_req.created_at if latest_fin_req else None,
                    } if latest_fin_req else None,
                    "milestone_status_counts": ms_status_map,
                })
        return Response(data)
    



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from dynamic_form.models import FormSubmission
from django.db.models import Count

class MultipleProposalsAPIView(APIView):
   """
    Returns applicants who have submitted more than one proposal, grouped by service.
    """
   permission_classes = [IsAuthenticated]

   def get(self, request, *args, **kwargs):
        # Step 1: Find applicant emails with >1 unique service
        multi_service_applicants = (
            FormSubmission.objects
            .values('applicant__email', 'applicant__full_name')
            .annotate(service_count=Count('service', distinct=True))
            .filter(service_count__gt=1)
        )

        # Step 2: For each, list all their services
        result = []
        for applicant in multi_service_applicants:
            services = (
                FormSubmission.objects
                .filter(applicant__email=applicant['applicant__email'])
                .values_list('service__name', flat=True)
                .distinct()
            )
            result.append({
                'applicant__email': applicant['applicant__email'],
                'applicant__full_name': applicant['applicant__full_name'],
                'services': list(services),
                'service_count': applicant['service_count'],
            })

        return Response({"applicants_with_multiple_services": result})
    

