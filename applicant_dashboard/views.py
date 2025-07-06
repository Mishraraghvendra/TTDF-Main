from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta, datetime
from django.shortcuts import get_object_or_404

from .models import DashboardStats, UserActivity, DraftApplication
from .serializers import (
    DashboardStatsSerializer, UserActivitySerializer, DraftApplicationSerializer,
    ProposalSummarySerializer
)
from dynamic_form.models import FormSubmission
from screening.models import ScreeningRecord, TechnicalScreeningRecord
from tech_eval.models import TechnicalEvaluationRound, EvaluatorAssignment
from presentation.models import Presentation

from milestones.models import (
    Milestone, SubMilestone, MilestoneDocument, SubMilestoneDocument,
    FinanceRequest, PaymentClaim, FinanceSanction
)


class DashboardOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        try:
            stats, created = DashboardStats.objects.get_or_create(user=user)
            if created or (timezone.now() - stats.last_updated).seconds > 300:
                stats.refresh_stats()

            recent_activities = UserActivity.objects.filter(user=user)[:10]
            draft_applications = DraftApplication.objects.filter(user=user).select_related('submission')
            recent_proposals = FormSubmission.objects.filter(
                applicant=user
            ).exclude(status=FormSubmission.DRAFT).order_by('-updated_at')[:5]
            current_calls = self._get_current_calls()

            dashboard_data = {
                'stats': DashboardStatsSerializer(stats).data,
                'recent_activities': UserActivitySerializer(recent_activities, many=True).data,
                'draft_applications': DraftApplicationSerializer(draft_applications, many=True).data,
                'current_calls': current_calls,
                'recent_proposals': ProposalSummarySerializer(recent_proposals, many=True).data,
            }

            return Response({
                'status': 'success',
                'data': dashboard_data
            })
        
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error loading dashboard: {str(e)}',
                'data': {}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_current_calls(self):
        try:
            from configuration.models import Service
            
            services = Service.objects.filter(is_active=True)
            calls = []
            
            for service in services:
                now = timezone.now()
                is_active = True
                
                if hasattr(service, 'start_date') and hasattr(service, 'end_date'):
                    if service.start_date and service.end_date:
                        is_active = service.start_date <= now <= service.end_date
                    elif service.end_date:
                        is_active = now <= service.end_date

                call_data = {
                    "title": service.name or "",
                    "description": getattr(service, 'description', '') or "",
                    "start_date": getattr(service, 'start_date', None),
                    "end_date": getattr(service, 'end_date', None),
                    "posted_date": service.created_at.strftime('%Y-%m-%d') if hasattr(service, 'created_at') and service.created_at else "",
                    "status": "Active" if is_active else "Inactive",
                }
                calls.append(call_data)
            
            return calls[:10]
        except Exception:
            return []


class ProposalStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        try:
            proposals = FormSubmission.objects.filter(applicant=user)
            
            stats = {
                'Submitted': [],
                'Screening': [], 
                'Evaluation': [],
                'Interview': [],
                'Approved': [],
                'Not Shortlisted': [],
                'History': [],
            }

            for proposal in proposals.exclude(status=FormSubmission.DRAFT):
                proposal_data = self._build_proposal_data(proposal)
                category = self._categorize_proposal(proposal)
                
                if category in stats:
                    stats[category].append(proposal_data)

            return Response({
                'status': 'success',
                'data': stats
            })
        
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error loading proposal stats: {str(e)}',
                'data': {}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _build_proposal_data(self, proposal):
        proposal_date = proposal.updated_at or proposal.created_at
        
        days_pending = 0
        if proposal_date:
            days_pending = max(0, (timezone.now() - proposal_date).days)
        
        return {
            "title": proposal.service.name if proposal.service else "",
            "proposalId": proposal.proposal_id or proposal.form_id or "",
            "status": self._get_display_status(proposal),
            "date": proposal_date.strftime("%d %b %Y") if proposal_date else "",
            "remarks": self._get_remarks(proposal),
            "daysPending": days_pending,
        }

    def _categorize_proposal(self, proposal):
        latest_screening = proposal.screening_records.order_by('-cycle').first()
        tech_eval = proposal.technical_evaluation_rounds.first()
        presentation = proposal.presentations.first()

        if presentation:
            if presentation.final_decision == 'shortlisted':
                return 'Approved'
            elif presentation.final_decision in ['not_shortlisted', 'rejected']:
                return 'Not Shortlisted'
            elif presentation.final_decision in ['pending', 'assigned', 'evaluated']:
                return 'Interview'

        if proposal.status == FormSubmission.APPROVED:
            return 'Approved'
        elif proposal.status == FormSubmission.REJECTED:
            return 'Not Shortlisted'

        if proposal.status == FormSubmission.SUBMITTED:
            if not latest_screening:
                return 'Submitted'
            
            if latest_screening.admin_decision == 'pending':
                return 'Submitted'
            elif latest_screening.admin_decision == 'not shortlisted':
                return 'Not Shortlisted'
            elif latest_screening.admin_decision == 'shortlisted':
                tech_record = getattr(latest_screening, 'technical_record', None)
                if not tech_record:
                    return 'Screening'
                
                if tech_record.technical_decision == 'pending':
                    return 'Screening'
                elif tech_record.technical_decision == 'not shortlisted':
                    return 'Not Shortlisted'
                elif tech_record.technical_decision == 'shortlisted':
                    if not tech_eval:
                        return 'Evaluation'
                    
                    if tech_eval.assignment_status == 'pending':
                        return 'Evaluation'
                    elif tech_eval.assignment_status == 'assigned':
                        return 'Evaluation'
                    elif tech_eval.assignment_status == 'completed':
                        if tech_eval.overall_decision == 'recommended':
                            if not presentation:
                                return 'Interview'
                            return 'Interview'
                        elif tech_eval.overall_decision == 'not_recommended':
                            return 'Not Shortlisted'
                        else:
                            return 'Evaluation'
                    else:
                        return 'Evaluation'
                else:
                    return 'Not Shortlisted'
            else:
                return 'Not Shortlisted'
        
        return 'History'

    def _get_display_status(self, proposal):
        category = self._categorize_proposal(proposal)
        
        if category == 'Not Shortlisted':
            latest_screening = proposal.screening_records.order_by('-cycle').first()
            tech_eval = proposal.technical_evaluation_rounds.first()
            presentation = proposal.presentations.first()
            
            if presentation and presentation.final_decision in ['not_shortlisted', 'rejected']:
                return 'Not Selected (Interview Stage)'
            
            if tech_eval and tech_eval.overall_decision == 'not_recommended':
                return 'Not Selected (Technical Evaluation)'
            
            if latest_screening and hasattr(latest_screening, 'technical_record'):
                tech_record = latest_screening.technical_record
                if tech_record and tech_record.technical_decision == 'not shortlisted':
                    return 'Not Selected (Technical Screening)'
            
            if latest_screening and latest_screening.admin_decision == 'not shortlisted':
                return 'Not Selected (Admin Screening)'
            
            return 'Not Selected'
        
        status_map = {
            'Submitted': 'Referred',
            'Screening': 'Under Screening', 
            'Evaluation': 'Under Evaluation',
            'Interview': 'Interview Stage',
            'Approved': 'Approved',
            'History': 'Completed'
        }
        
        return status_map.get(category, '')

    def _get_remarks(self, proposal):
        category = self._categorize_proposal(proposal)
        
        if category != 'Not Shortlisted':
            return "No remarks available"
        
        latest_screening = proposal.screening_records.order_by('-cycle').first()
        tech_eval = proposal.technical_evaluation_rounds.first()
        presentation = proposal.presentations.first()
        
        remarks_list = []
        
        if presentation and presentation.final_decision in ['not_shortlisted', 'rejected']:
            stage_name = "Interview Stage"
            
            if presentation.admin_remarks:
                admin_name = presentation.admin.get_full_name() if presentation.admin else "Admin"
                remarks_list.append(f"[{stage_name} - Admin: {admin_name}] {presentation.admin_remarks}")
            
            if presentation.evaluator_remarks:
                evaluator_name = presentation.evaluator.get_full_name() if presentation.evaluator else "Evaluator"
                remarks_list.append(f"[{stage_name} - Evaluator: {evaluator_name}] {presentation.evaluator_remarks}")
            
            if remarks_list:
                return " | ".join(remarks_list)
        
        if tech_eval and tech_eval.overall_decision == 'not_recommended':
            stage_name = "Technical Evaluation"
            
            for assignment in tech_eval.evaluator_assignments.filter(is_completed=True):
                evaluator_name = assignment.evaluator.get_full_name() if assignment.evaluator else "Evaluator"
                
                if assignment.overall_comments:
                    remarks_list.append(f"[{stage_name} - Evaluator: {evaluator_name}] {assignment.overall_comments}")
                
                for criteria_eval in assignment.criteria_evaluations.all():
                    if criteria_eval.remarks:
                        criteria_name = criteria_eval.evaluation_criteria.name
                        remarks_list.append(f"[{stage_name} - Evaluator: {evaluator_name} on {criteria_name}] {criteria_eval.remarks}")
            
            if remarks_list:
                return " | ".join(remarks_list)
        
        if latest_screening and hasattr(latest_screening, 'technical_record'):
            tech_record = latest_screening.technical_record
            if tech_record and tech_record.technical_decision == 'not shortlisted':
                stage_name = "Technical Screening"
                
                if tech_record.technical_remarks:
                    screener_name = tech_record.technical_evaluator.get_full_name() if tech_record.technical_evaluator else "Technical Screener"
                    remarks_list.append(f"[{stage_name} - {screener_name}] {tech_record.technical_remarks}")
                
                if remarks_list:
                    return " | ".join(remarks_list)
        
        if latest_screening and latest_screening.admin_decision == 'not shortlisted':
            stage_name = "Admin Screening"
            
            if latest_screening.admin_remarks:
                admin_name = latest_screening.admin_evaluator.get_full_name() if latest_screening.admin_evaluator else "Admin Screener"
                remarks_list.append(f"[{stage_name} - {admin_name}] {latest_screening.admin_remarks}")
            
            if remarks_list:
                return " | ".join(remarks_list)
        
        return "No remarks available"


class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserActivity.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        try:
            activity = self.get_object()
            activity.is_read = True
            activity.save()
            return Response({'status': 'success', 'message': 'Activity marked as read'})
        except Exception as e:
            return Response({
                'status': 'error', 
                'message': f'Error marking activity as read: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        try:
            self.get_queryset().update(is_read=True)
            return Response({'status': 'success', 'message': 'All activities marked as read'})
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error marking all activities as read: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        try:
            count = self.get_queryset().filter(is_read=False).count()
            return Response({'unread_count': count})
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error getting unread count: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CallsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            from configuration.models import Service
            
            services = Service.objects.all().order_by('-created_at')
            current_calls = []
            previous_calls = []
            
            for service in services:
                now = timezone.now()
                is_active = True
                
                if hasattr(service, 'start_date') and hasattr(service, 'end_date'):
                    if service.start_date and service.end_date:
                        is_active = service.start_date <= now <= service.end_date
                    elif service.end_date:
                        is_active = now <= service.end_date

                call_data = {
                    "id": service.id,
                    "template_id": str(service.template_id) if hasattr(service, "template_id") and service.template_id else None,
                    "title": service.name or "",
                    "description": getattr(service, 'description', '') or "",
                    "start_date": service.start_date.strftime('%Y-%m-%d') if hasattr(service, 'start_date') and service.start_date else "",
                    "end_date": service.end_date.strftime('%Y-%m-%d') if hasattr(service, 'end_date') and service.end_date else "",
                    "posted_date": service.created_at.strftime('%Y-%m-%d') if hasattr(service, 'created_at') and service.created_at else "",
                    "status": "Active" if is_active else "Inactive",
                }
                
                if is_active:
                    current_calls.append(call_data)
                else:
                    previous_calls.append(call_data)

            return Response({
                'status': 'success',
                'data': {
                    'current_calls': current_calls,
                    'previous_calls': previous_calls
                }
            })
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error loading calls: {str(e)}',
                'data': {
                    'current_calls': [],
                    'previous_calls': []
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProjectMilestonesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, proposal_id=None):
        if not proposal_id:
            return Response({
                'status': 'error',
                'message': 'Proposal ID is required',
                'data': []
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            proposal = get_object_or_404(
                FormSubmission, 
                Q(proposal_id=proposal_id) | Q(form_id=proposal_id),
                applicant=request.user
            )

            milestones = Milestone.objects.filter(proposal=proposal).prefetch_related(
                'submilestones', 
                'documents',
                'submilestones__documents'
            ).order_by('created_at')
            
            if not milestones.exists():
                return Response({
                    'status': 'success',
                    'message': 'No milestones found for this proposal',
                    'data': []
                })
            
            milestone_data = []
            for milestone in milestones:
                milestone_dict = {
                    'id': milestone.id,
                    'title': milestone.title or "",
                    'time_required': milestone.time_required,
                    'revised_time_required': milestone.revised_time_required,
                    'grant_from_ttdf': milestone.grant_from_ttdf,
                    'initial_contri_applicant': milestone.initial_contri_applicant,
                    'revised_contri_applicant': milestone.revised_contri_applicant,
                    'initial_grant_from_ttdf': milestone.initial_grant_from_ttdf,
                    'revised_grant_from_ttdf': milestone.revised_grant_from_ttdf,
                    'status': milestone.status or "",
                    'due_date': milestone.due_date,
                    'created_at': milestone.created_at,
                    'updated_at': milestone.updated_at,
                    'description': milestone.description or "",
                    'proposal': {
                        'proposal_id': proposal.proposal_id or proposal.form_id or "",
                        'service': {
                            'name': proposal.service.name if proposal.service else ""
                        },
                        'created_at': proposal.created_at
                    },
                    'submilestones': [],
                    'documents': []
                }
                
                for submilestone in milestone.submilestones.all():
                    sub_dict = {
                        'id': submilestone.id,
                        'title': submilestone.title or "",
                        'time_required': submilestone.time_required,
                        'revised_time_required': submilestone.revised_time_required,
                        'grant_from_ttdf': submilestone.grant_from_ttdf,
                        'initial_contri_applicant': submilestone.initial_contri_applicant,
                        'revised_contri_applicant': submilestone.revised_contri_applicant,
                        'initial_grant_from_ttdf': submilestone.initial_grant_from_ttdf,
                        'revised_grant_from_ttdf': submilestone.revised_grant_from_ttdf,
                        'status': submilestone.status or "",
                        'due_date': submilestone.due_date,
                        'created_at': submilestone.created_at,
                        'updated_at': submilestone.updated_at,
                        'description': submilestone.description or "",
                        'documents': []
                    }
                    
                    for sub_doc in submilestone.documents.all():
                        sub_doc_dict = {
                            'id': sub_doc.id,
                            'mpr': sub_doc.mpr.url if sub_doc.mpr else None,
                            'mpr_status': sub_doc.mpr_status or "",
                            'mcr': sub_doc.mcr.url if sub_doc.mcr else None,
                            'mcr_status': sub_doc.mcr_status or "",
                            'uc': sub_doc.uc.url if sub_doc.uc else None,
                            'uc_status': sub_doc.uc_status or "",
                            'assets': sub_doc.assets.url if sub_doc.assets else None,
                            'assets_status': sub_doc.assets_status or "",
                            'uploaded_at': sub_doc.uploaded_at,
                        }
                        sub_dict['documents'].append(sub_doc_dict)
                    
                    milestone_dict['submilestones'].append(sub_dict)
                
                for doc in milestone.documents.all():
                    doc_dict = {
                        'id': doc.id,
                        'mpr': doc.mpr.url if doc.mpr else None,
                        'mpr_status': doc.mpr_status or "",
                        'mcr': doc.mcr.url if doc.mcr else None,
                        'mcr_status': doc.mcr_status or "",
                        'uc': doc.uc.url if doc.uc else None,
                        'uc_status': doc.uc_status or "",
                        'assets': doc.assets.url if doc.assets else None,
                        'assets_status': doc.assets_status or "",
                        'uploaded_at': doc.uploaded_at,
                    }
                    milestone_dict['documents'].append(doc_dict)
                
                milestone_data.append(milestone_dict)

            return Response({
                'status': 'success',
                'data': milestone_data
            })

        except FormSubmission.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Proposal not found or access denied',
                'data': []
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error loading milestones: {str(e)}',
                'data': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FinanceDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, proposal_id=None):
        if not proposal_id:
            return Response({
                'status': 'error',
                'message': 'Proposal ID is required',
                'data': []
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            proposal = get_object_or_404(
                FormSubmission, 
                Q(proposal_id=proposal_id) | Q(form_id=proposal_id),
                applicant=request.user
            )

            sanctions = FinanceSanction.objects.filter(
                proposal=proposal
            ).select_related(
                'finance_request__milestone',
                'finance_request__submilestone',
                'payment_claim'
            ).order_by('-sanction_date')
            
            if not sanctions.exists():
                return Response({
                    'status': 'success',
                    'message': 'No finance data found for this proposal',
                    'data': []
                })
            
            finance_data = []
            for sanction in sanctions:
                sanction_dict = {
                    'id': sanction.id,
                    'sanction_amount': float(sanction.sanction_amount) if sanction.sanction_amount else 0,
                    'sanction_date': sanction.sanction_date,
                    'status': sanction.status or "",
                    'sanction_note': sanction.sanction_note or "",
                    'jf_remark': sanction.jf_remark or "",
                    'created_at': sanction.created_at,
                    'reviewed_at': sanction.reviewed_at,
                    'finance_request': None,
                    'payment_claim': None,
                    'proposal': {
                        'proposal_id': proposal.proposal_id or proposal.form_id or "",
                        'service': {
                            'name': proposal.service.name if proposal.service else ""
                        },
                        'applicant': {
                            'name': f"{proposal.applicant.first_name} {proposal.applicant.last_name}".strip() if proposal.applicant else ""
                        },
                        'created_at': proposal.created_at
                    }
                }
                
                if sanction.finance_request:
                    finance_req_dict = {
                        'id': sanction.finance_request.id,
                        'status': sanction.finance_request.status or "",
                        'ia_remark': sanction.finance_request.ia_remark or "",
                        'created_at': sanction.finance_request.created_at,
                        'reviewed_at': sanction.finance_request.reviewed_at,
                        'milestone': None,
                        'submilestone': None
                    }
                    
                    if sanction.finance_request.milestone:
                        milestone = sanction.finance_request.milestone
                        finance_req_dict['milestone'] = {
                            'id': milestone.id,
                            'title': milestone.title or "",
                            'revised_grant_from_ttdf': milestone.revised_grant_from_ttdf,
                            'revised_contri_applicant': milestone.revised_contri_applicant,
                            'status': milestone.status or ""
                        }
                    
                    if sanction.finance_request.submilestone:
                        submilestone = sanction.finance_request.submilestone
                        finance_req_dict['submilestone'] = {
                            'id': submilestone.id,
                            'title': submilestone.title or "",
                            'revised_grant_from_ttdf': submilestone.revised_grant_from_ttdf,
                            'revised_contri_applicant': submilestone.revised_contri_applicant,
                            'status': submilestone.status or ""
                        }
                    
                    sanction_dict['finance_request'] = finance_req_dict
                
                if sanction.payment_claim:
                    payment_claim_dict = {
                        'id': sanction.payment_claim.id,
                        'status': sanction.payment_claim.status or "",
                        'ia_action': sanction.payment_claim.ia_action or "",
                        'ia_remark': sanction.payment_claim.ia_remark or "",
                        'jf_remark': sanction.payment_claim.jf_remark or "",
                        'advance_payment': sanction.payment_claim.advance_payment,
                        'penalty_amount': float(sanction.payment_claim.penalty_amount) if sanction.payment_claim.penalty_amount else 0,
                        'ld': float(sanction.payment_claim.ld) if sanction.payment_claim.ld else 0,
                        'adjustment_amount': float(sanction.payment_claim.adjustment_amount) if sanction.payment_claim.adjustment_amount else 0,
                        'net_claim_amount': float(sanction.payment_claim.net_claim_amount) if sanction.payment_claim.net_claim_amount else 0,
                        'created_at': sanction.payment_claim.created_at,
                        'reviewed_at': sanction.payment_claim.reviewed_at,
                    }
                    sanction_dict['payment_claim'] = payment_claim_dict
                
                finance_data.append(sanction_dict)

            return Response({
                'status': 'success',
                'data': finance_data
            })

        except FormSubmission.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Proposal not found or access denied',
                'data': []
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error loading finance data: {str(e)}',
                'data': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            milestone_id = request.data.get('milestone')
            submilestone_id = request.data.get('submilestone')
            document_type = request.data.get('document_type', 'mpr').lower()
            
            if not milestone_id:
                return Response({
                    'status': 'error',
                    'message': 'Milestone ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            milestone = get_object_or_404(Milestone, id=milestone_id)
            
            if milestone.proposal.applicant != request.user:
                return Response({
                    'status': 'error',
                    'message': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)

            if submilestone_id:
                submilestone = get_object_or_404(SubMilestone, id=submilestone_id, milestone=milestone)
                doc, created = SubMilestoneDocument.objects.get_or_create(submilestone=submilestone)
                document_model = doc
                document_name = "SubMilestone Document"
                related_object = submilestone
            else:
                doc, created = MilestoneDocument.objects.get_or_create(milestone=milestone)
                document_model = doc
                document_name = "Milestone Document"
                related_object = milestone
            
            file_field_map = {
                'mpr': 'mpr',
                'uc': 'uc', 
                'mcr': 'mcr',
                'scr': 'mcr',
                'ac': 'assets',
                'assets': 'assets'
            }
            
            field_name = file_field_map.get(document_type)
            if not field_name:
                return Response({
                    'status': 'error',
                    'message': f'Invalid document type: {document_type}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if field_name in request.FILES:
                setattr(document_model, field_name, request.FILES[field_name])
                status_field = f'{field_name}_status'
                setattr(document_model, status_field, 'pending')
                document_model.save()
                
                activity_type = 'documents_requested'
                title = f"{document_name} Uploaded"
                description = f"Uploaded {document_type.upper()} document for {milestone.title or 'milestone'}"
                if submilestone_id:
                    description += f" - {submilestone.title or 'submilestone'}"
                
                UserActivity.objects.create(
                    user=request.user,
                    activity_type=activity_type,
                    title=title,
                    description=description,
                    related_submission=milestone.proposal
                )
                
                return Response({
                    'status': 'success',
                    'message': f'{document_type.upper()} document uploaded successfully',
                    'data': {
                        'id': document_model.id,
                        'document_type': document_type,
                        'uploaded_at': document_model.uploaded_at,
                        'status': getattr(document_model, status_field, ''),
                        'milestone_id': milestone_id,
                        'submilestone_id': submilestone_id,
                        'file_url': getattr(document_model, field_name).url if getattr(document_model, field_name) else None
                    }
                })
            else:
                return Response({
                    'status': 'error',
                    'message': f'No file provided for {document_type}'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Milestone.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Milestone not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except SubMilestone.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Submilestone not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Upload failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class ProposalDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, proposal_id):
        try:
            proposal = get_object_or_404(
                FormSubmission, 
                Q(proposal_id=proposal_id) | Q(form_id=proposal_id),
                applicant=request.user
            )

            details = {
                'proposalId': proposal.proposal_id or proposal.form_id,
                'title': proposal.service.name if proposal.service else 'Untitled',
                'status': proposal.status,
                'submittedDate': proposal.created_at.strftime('%Y-%m-%d') if proposal.created_at else None,
                'workflow': self._build_workflow_timeline(proposal),
                'screening': self._get_screening_details(proposal),
                'technicalEvaluation': self._get_technical_evaluation_details(proposal),
                'presentation': self._get_presentation_details(proposal)
            }

            return Response({
                'status': 'success',
                'data': details
            })

        except FormSubmission.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Proposal not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error loading proposal details: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _build_workflow_timeline(self, proposal):
        timeline = []
        
        timeline.append({
            'stage': 'submitted',
            'title': 'Proposal Submitted',
            'status': 'completed',
            'date': proposal.created_at.strftime('%Y-%m-%d %H:%M') if proposal.created_at else None,
            'remarks': None
        })

        latest_screening = proposal.screening_records.order_by('-cycle').first()
        if latest_screening:
            screening_stage = {
                'stage': 'screening',
                'title': 'Administrative Screening',
                'status': 'completed' if latest_screening.admin_decision != 'pending' else 'in_progress',
                'date': latest_screening.admin_screened_at.strftime('%Y-%m-%d %H:%M') if latest_screening.admin_screened_at else None,
                'evaluator': latest_screening.admin_evaluator.get_full_name() if latest_screening.admin_evaluator else None,
                'remarks': latest_screening.admin_remarks if latest_screening.admin_remarks else None
            }
            timeline.append(screening_stage)

            tech_record = getattr(latest_screening, 'technical_record', None)
            if tech_record:
                tech_screening_stage = {
                    'stage': 'technical_screening',
                    'title': 'Technical Screening',
                    'status': 'completed' if tech_record.technical_decision != 'pending' else 'in_progress',
                    'date': tech_record.technical_screened_at.strftime('%Y-%m-%d %H:%M') if tech_record.technical_screened_at else None,
                    'evaluator': tech_record.technical_evaluator.get_full_name() if tech_record.technical_evaluator else None,
                    'remarks': tech_record.technical_remarks if tech_record.technical_remarks else None
                }
                timeline.append(tech_screening_stage)

        tech_eval = proposal.technical_evaluation_rounds.first()
        if tech_eval:
            eval_stage = {
                'stage': 'evaluation',
                'title': 'Technical Evaluation',
                'status': 'completed' if tech_eval.assignment_status == 'completed' else 'in_progress',
                'date': tech_eval.completed_at.strftime('%Y-%m-%d %H:%M') if tech_eval.completed_at else None,
                'remarks': None
            }
            
            evaluator_remarks = []
            for assignment in tech_eval.evaluator_assignments.filter(is_completed=True):
                if assignment.overall_comments:
                    evaluator_name = assignment.evaluator.get_full_name() if assignment.evaluator else 'Evaluator'
                    evaluator_remarks.append(f"{evaluator_name}: {assignment.overall_comments}")
            
            if evaluator_remarks:
                eval_stage['remarks'] = " | ".join(evaluator_remarks)
            
            timeline.append(eval_stage)

        presentation = proposal.presentations.first()
        if presentation:
            pres_stage = {
                'stage': 'interview',
                'title': 'Presentation/Interview',
                'status': 'completed' if presentation.final_decision != 'pending' else 'in_progress',
                'date': presentation.admin_evaluated_at.strftime('%Y-%m-%d %H:%M') if presentation.admin_evaluated_at else None,
                'evaluator': presentation.evaluator.get_full_name() if presentation.evaluator else None,
                'remarks': None
            }
            
            remarks_parts = []
            if presentation.admin_remarks:
                admin_name = presentation.admin.get_full_name() if presentation.admin else 'Admin'
                remarks_parts.append(f"Admin ({admin_name}): {presentation.admin_remarks}")
            if presentation.evaluator_remarks:
                evaluator_name = presentation.evaluator.get_full_name() if presentation.evaluator else 'Evaluator'
                remarks_parts.append(f"Evaluator ({evaluator_name}): {presentation.evaluator_remarks}")
            
            if remarks_parts:
                pres_stage['remarks'] = " | ".join(remarks_parts)
            
            timeline.append(pres_stage)

            if presentation.final_decision != 'pending':
                final_stage = {
                    'stage': 'approved' if presentation.final_decision == 'shortlisted' else 'rejected',
                    'title': 'Final Decision',
                    'status': 'completed',
                    'date': presentation.admin_evaluated_at.strftime('%Y-%m-%d %H:%M') if presentation.admin_evaluated_at else None,
                    'evaluator': presentation.admin.get_full_name() if presentation.admin else None,
                    'remarks': presentation.admin_remarks if presentation.admin_remarks else None
                }
                timeline.append(final_stage)

        return timeline

    def _get_screening_details(self, proposal):
        latest_screening = proposal.screening_records.order_by('-cycle').first()
        if not latest_screening:
            return None

        current_category = self._categorize_proposal(proposal)
        tech_eval = proposal.technical_evaluation_rounds.first()
        presentation = proposal.presentations.first()
        
        if current_category in ['Interview', 'Evaluation', 'Approved']:
            admin_decision = 'shortlisted'
            technical_decision = 'shortlisted'
        else:
            admin_decision = latest_screening.admin_decision
            tech_record = getattr(latest_screening, 'technical_record', None)
            technical_decision = tech_record.technical_decision if tech_record else None

        screening_details = {
            'adminDecision': admin_decision,
            'adminRemarks': latest_screening.admin_remarks,
            'adminEvaluator': latest_screening.admin_evaluator.get_full_name() if latest_screening.admin_evaluator else None,
            'screenedAt': latest_screening.admin_screened_at.strftime('%Y-%m-%d %H:%M') if latest_screening.admin_screened_at else None
        }

        tech_record = getattr(latest_screening, 'technical_record', None)
        if tech_record:
            screening_details.update({
                'technicalDecision': technical_decision,
                'technicalRemarks': tech_record.technical_remarks,
                'technicalEvaluator': tech_record.technical_evaluator.get_full_name() if tech_record.technical_evaluator else None,
                'technicalScreenedAt': tech_record.technical_screened_at.strftime('%Y-%m-%d %H:%M') if tech_record.technical_screened_at else None
            })

        return screening_details

    def _categorize_proposal(self, proposal):
        latest_screening = proposal.screening_records.order_by('-cycle').first()
        tech_eval = proposal.technical_evaluation_rounds.first()
        presentation = proposal.presentations.first()

        if presentation:
            if presentation.final_decision == 'shortlisted':
                return 'Approved'
            elif presentation.final_decision in ['not_shortlisted', 'rejected']:
                return 'Not Shortlisted'
            elif presentation.final_decision in ['pending', 'assigned', 'evaluated']:
                return 'Interview'

        if proposal.status == FormSubmission.APPROVED:
            return 'Approved'
        elif proposal.status == FormSubmission.REJECTED:
            return 'Not Shortlisted'

        if proposal.status == FormSubmission.SUBMITTED:
            if not latest_screening:
                return 'Submitted'
            
            if latest_screening.admin_decision == 'pending':
                return 'Submitted'
            elif latest_screening.admin_decision == 'not shortlisted':
                return 'Not Shortlisted'
            elif latest_screening.admin_decision == 'shortlisted':
                tech_record = getattr(latest_screening, 'technical_record', None)
                if not tech_record:
                    return 'Screening'
                
                if tech_record.technical_decision == 'pending':
                    return 'Screening'
                elif tech_record.technical_decision == 'not shortlisted':
                    return 'Not Shortlisted'
                elif tech_record.technical_decision == 'shortlisted':
                    if not tech_eval:
                        return 'Evaluation'
                    
                    if tech_eval.assignment_status == 'pending':
                        return 'Evaluation'
                    elif tech_eval.assignment_status == 'assigned':
                        return 'Evaluation'
                    elif tech_eval.assignment_status == 'completed':
                        if tech_eval.overall_decision == 'recommended':
                            if not presentation:
                                return 'Interview'
                            return 'Interview'
                        elif tech_eval.overall_decision == 'not_recommended':
                            return 'Not Shortlisted'
                        else:
                            return 'Evaluation'
                    else:
                        return 'Evaluation'
                else:
                    return 'Not Shortlisted'
            else:
                return 'Not Shortlisted'
        
        return 'History'

    def _get_technical_evaluation_details(self, proposal):
        tech_eval = proposal.technical_evaluation_rounds.first()
        if not tech_eval:
            return None

        evaluation_details = {
            'assignmentStatus': tech_eval.assignment_status,
            'overallDecision': tech_eval.overall_decision,
            'completedAt': tech_eval.completed_at.strftime('%Y-%m-%d %H:%M') if tech_eval.completed_at else None,
            'evaluators': []
        }

        for assignment in tech_eval.evaluator_assignments.all():
            evaluator_data = {
                'name': assignment.evaluator.get_full_name() if assignment.evaluator else 'Unknown',
                'email': assignment.evaluator.email if assignment.evaluator else None,
                'isCompleted': assignment.is_completed,
                'overallComments': assignment.overall_comments,
                'conflictOfInterest': assignment.conflict_of_interest,
                'completedAt': assignment.completed_at.strftime('%Y-%m-%d %H:%M') if assignment.completed_at else None,
                'criteriaEvaluations': []
            }

            for criteria_eval in assignment.criteria_evaluations.all():
                criteria_data = {
                    'name': criteria_eval.evaluation_criteria.name,
                    'marks': float(criteria_eval.marks_given),
                    'maxMarks': float(criteria_eval.evaluation_criteria.total_marks),
                    'percentage': criteria_eval.percentage_score,
                    'remarks': criteria_eval.remarks
                }
                evaluator_data['criteriaEvaluations'].append(criteria_data)

            evaluation_details['evaluators'].append(evaluator_data)

        return evaluation_details

    def _get_presentation_details(self, proposal):
        presentation = proposal.presentations.first()
        if not presentation:
            return None

        return {
            'finalDecision': presentation.final_decision,
            'presentationDate': presentation.presentation_date.strftime('%Y-%m-%d %H:%M') if presentation.presentation_date else None,
            'evaluator': presentation.evaluator.get_full_name() if presentation.evaluator else None,
            'evaluatorRemarks': presentation.evaluator_remarks,
            'admin': presentation.admin.get_full_name() if presentation.admin else None,
            'adminRemarks': presentation.admin_remarks,
            'evaluatedAt': presentation.evaluated_at.strftime('%Y-%m-%d %H:%M') if presentation.evaluated_at else None,
            'adminEvaluatedAt': presentation.admin_evaluated_at.strftime('%Y-%m-%d %H:%M') if presentation.admin_evaluated_at else None
        }


class RefreshStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            stats, created = DashboardStats.objects.get_or_create(user=request.user)
            stats.refresh_stats()
            
            return Response({
                'status': 'success',
                'message': 'Dashboard statistics refreshed successfully',
                'data': DashboardStatsSerializer(stats).data
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error refreshing stats: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)