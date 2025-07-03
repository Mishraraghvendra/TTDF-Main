# proposal_aggregate/api/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from dynamic_form.models import FormSubmission
from .serializers import ProposalDetailSerializer

class ProposalDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/proposals/{proposal_id}/
    Returns a full snapshot of a proposal across all apps.
    """
    queryset = FormSubmission.objects.all().prefetch_related(
        'responses__field', 'status_history',
        'applications__stage_progress', 'applications__screening_results',
        'eval_assignments__criteria_evaluations', 'eval_assignments__question_evaluations',
        'milestones__submilestones', 'milestones__finance_requests__payment_claim__finance_sanction',
        'presentations',
        'screening_records__technical_record',
        'technical_evaluations__criteria_evaluations',
    )
    serializer_class = ProposalDetailSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'proposal_id'

