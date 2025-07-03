from rest_framework.views import APIView 
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from configuration.models import Service
from users.models import User
from dynamic_form.models import FormSubmission
from tech_eval.models import TechnicalEvaluationRound,EvaluatorAssignment

from django.db.models import Count, Q, Max
from milestones.models import Milestone, SubMilestone

from screening.models import ScreeningRecord, TechnicalScreeningRecord
from django.db.models import OuterRef, Subquery
from tech_eval.models import TRLAnalysis
from presentation.models import Presentation



class AdminDashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # User counts
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()

        # Service counts
        total_services = Service.objects.count()
        active_services = Service.objects.filter(status='active').count()
        draft_services = Service.objects.filter(status='draft').count()

        # Service-wise stats
        services_data = []
        services = Service.objects.all()
        for service in services:
            proposals = FormSubmission.objects.filter(service=service)
            active_proposals = proposals.filter(status='submitted').count()
            draft_proposals = proposals.filter(status='draft').count()

            tech_evals = TechnicalEvaluationRound.objects.filter(proposal__in=proposals)
            proposals_under_eval = tech_evals.filter(overall_decision='pending').count()

            presentations = Presentation.objects.filter(proposal__in=proposals)
            shortlisted = presentations.filter(final_decision='shortlisted').count()
            not_shortlisted = presentations.filter(final_decision='rejected').count()

            services_data.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "total_proposals": proposals.count(),
                "active_proposals": active_proposals,
                "draft_proposals": draft_proposals,
                "proposals_under_evaluation": proposals_under_eval,
                "shortlisted_presentations": shortlisted,
                "not_shortlisted_presentations": not_shortlisted,
            })

        total_proposals_under_eval = TechnicalEvaluationRound.objects.filter(overall_decision='pending').count()
        total_shortlisted = Presentation.objects.filter(final_decision='shortlisted').count()
        total_not_shortlisted = Presentation.objects.filter(final_decision='rejected').count()

        return Response({
            "users": {
                "total": total_users,
                "active": active_users
            },
            "services": {
                "total": total_services,
                "active": active_services,
                "draft": draft_services
            },
            "proposals": {
                "under_evaluation": total_proposals_under_eval,
            },
            "presentations": {
                "shortlisted": total_shortlisted,
                "not_shortlisted": total_not_shortlisted,
            },
            "services_breakdown": services_data
        })

# class AdminDashboardSummaryView(APIView): 
#     permission_classes = [IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         # User counts
#         total_users = User.objects.count()
#         active_users = User.objects.filter(is_active=True).count()

#         # Service counts
#         total_services = Service.objects.count()
#         active_services = Service.objects.filter(status='active').count()
#         draft_services = Service.objects.filter(status='draft').count()

#         # ---- 1. TRL Growth ----
#         trl_growth = (
#             FormSubmission.objects
#             .values('current_trl')
#             .annotate(count=Count('id'))
#             .order_by('current_trl')
#         )
#         trl_growth_dict = {str(item['current_trl']): item['count'] for item in trl_growth if item['current_trl'] is not None}

#         # ---- 2. Screening Status (per service) ----
#         screening_status = []
#         services = Service.objects.all()
#         for service in services:
#             proposals = FormSubmission.objects.filter(service=service)
#             screening_records = ScreeningRecord.objects.filter(proposal__in=proposals)
#             total = proposals.count()
#             shortlisted = screening_records.filter(admin_decision='shortlisted').count()
#             rejected = screening_records.filter(admin_decision='not shortlisted').count()
#             screening_status.append({
#                 "service_id": str(service.id),
#                 "service_name": service.name,
#                 "total_proposals": total,
#                 "shortlisted": shortlisted,
#                 "rejected": rejected,
#             })

#         # ---- 3. Presentation Status (per service) ----
#         presentation_status = []
#         for service in services:
#             proposals = FormSubmission.objects.filter(service=service)
#             presentations = Presentation.objects.filter(proposal__in=proposals)
#             total = presentations.count()
#             shortlisted = presentations.filter(final_decision='shortlisted').count()
#             rejected = presentations.filter(final_decision='rejected').count()
#             presentation_status.append({
#                 "service_id": str(service.id),
#                 "service_name": service.name,
#                 "total_presentations": total,
#                 "shortlisted": shortlisted,
#                 "rejected": rejected,
#             })

#         # ---- 4. Latest Milestone/Submilestone (proposal wise) ----
#         latest_milestones = {}
#         proposals = FormSubmission.objects.all()
#         for proposal in proposals:
#             latest_milestone = (
#                 Milestone.objects
#                 .filter(proposal=proposal)
#                 .order_by('-created_at')
#                 .first()
#             )
#             latest_submilestone = (
#                 SubMilestone.objects
#                 .filter(milestone__proposal=proposal)
#                 .order_by('-created_at')
#                 .first()
#             )
#             latest_milestones[proposal.proposal_id or proposal.id] = {
#                 "milestone": {
#                     "id": str(latest_milestone.id) if latest_milestone else None,
#                     "title": latest_milestone.title if latest_milestone else None,
#                     "created_at": latest_milestone.created_at if latest_milestone else None,
#                 } if latest_milestone else None,
#                 "submilestone": {
#                     "id": str(latest_submilestone.id) if latest_submilestone else None,
#                     "title": latest_submilestone.title if latest_submilestone else None,
#                     "created_at": latest_submilestone.created_at if latest_submilestone else None,
#                 } if latest_submilestone else None,
#             }

#         # ---- Previous Service breakdown ----
#         services_data = []
#         for service in services:
#             proposals = FormSubmission.objects.filter(service=service)
#             active_proposals = proposals.filter(status='submitted').count()
#             draft_proposals = proposals.filter(status='draft').count()
#             tech_evals = TechnicalEvaluationRound.objects.filter(proposal__in=proposals)
#             proposals_under_eval = tech_evals.filter(overall_decision='pending').count()
#             presentations = Presentation.objects.filter(proposal__in=proposals)
#             shortlisted = presentations.filter(final_decision='shortlisted').count()
#             not_shortlisted = presentations.filter(final_decision='rejected').count()
#             services_data.append({
#                 "service_id": str(service.id),
#                 "service_name": service.name,
#                 "total_proposals": proposals.count(),
#                 "active_proposals": active_proposals,
#                 "draft_proposals": draft_proposals,
#                 "proposals_under_evaluation": proposals_under_eval,
#                 "shortlisted_presentations": shortlisted,
#                 "not_shortlisted_presentations": not_shortlisted,
#             })

#         total_proposals_under_eval = TechnicalEvaluationRound.objects.filter(overall_decision='pending').count()
#         total_shortlisted = Presentation.objects.filter(final_decision='shortlisted').count()
#         total_not_shortlisted = Presentation.objects.filter(final_decision='rejected').count()

#         return Response({
#             "users": {
#                 "total": total_users,
#                 "active": active_users
#             },
#             "services": {
#                 "total": total_services,
#                 "active": active_services,
#                 "draft": draft_services
#             },
#             "trl_growth": trl_growth_dict,
#             "screening_status": screening_status,
#             "presentation_status": presentation_status,
#             "latest_milestones": latest_milestones,
#             "proposals": {
#                 "under_evaluation": total_proposals_under_eval,
#             },
#             "presentations": {
#                 "shortlisted": total_shortlisted,
#                 "not_shortlisted": total_not_shortlisted,
#             },
#             "services_breakdown": services_data
#         })

class EvaluatorDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        if not user.is_evaluator:
            return Response({"detail": "Not authorized. Evaluator access only."}, status=403)

        # All evaluator assignments
        eval_assignments = EvaluatorAssignment.objects.filter(evaluator=user)
        assigned_proposals = FormSubmission.objects.filter(
            technical_evaluation_rounds__evaluator_assignments__in=eval_assignments
        ).distinct()

        total_assigned = eval_assignments.count()
        total_completed = eval_assignments.filter(is_completed=True).count()

        # Status-wise summary
        proposal_status_summary = dict(
            assigned_proposals
            .values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )

        # Presentations assigned to evaluator
        presentations = Presentation.objects.filter(evaluator=user)
        total_presentations = presentations.count()
        evaluated_presentations = presentations.filter(evaluator_marks__isnull=False).count()

        # Service-wise proposal breakdown
        service_data = []
        services = Service.objects.filter(form_submissions__in=assigned_proposals).distinct()

        for service in services:
            proposals_in_service = assigned_proposals.filter(service=service)
            service_data.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "assigned_proposals": proposals_in_service.count(),
                "evaluated_proposals": proposals_in_service.filter(
                    technical_evaluation_rounds__evaluator_assignments__evaluator=user,
                    technical_evaluation_rounds__evaluator_assignments__is_completed=True
                ).distinct().count()
            })

        return Response({
            "proposals": {
                "assigned": total_assigned,
                "evaluated": total_completed,
                "by_status": proposal_status_summary
            },
            "presentations": {
                "assigned": total_presentations,
                "evaluated": evaluated_presentations
            },
            "service_breakdown": service_data
        })


# class UserServiceSummaryView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         total_users = User.objects.count()
#         active_users = User.objects.filter(is_active=True).count()
#         total_services = Service.objects.count()
#         active_services = Service.objects.filter(status='active').count()
#         draft_services = Service.objects.filter(status='draft').count()
#         return Response({
#             "users": {
#                 "total": total_users,
#                 "active": active_users
#             },
#             "services": {
#                 "total": total_services,
#                 "active": active_services,
#                 "draft": draft_services
#             }
#         })

# class TRLGrowthView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         trl_growth = (
#             FormSubmission.objects
#             .exclude(current_trl__isnull=True)
#             .values('current_trl')
#             .annotate(count=Count('id'))
#             .order_by('current_trl')
#         )
#         trl_growth_dict = {str(item['current_trl']): item['count'] for item in trl_growth}
#         return Response({"trl_growth": trl_growth_dict})

# class ScreeningStatusView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         services = Service.objects.all()
#         data = []
#         for service in services:
#             proposals = FormSubmission.objects.filter(service=service)
#             screening_records = ScreeningRecord.objects.filter(proposal__in=proposals)
#             total = proposals.count()
#             shortlisted = screening_records.filter(admin_decision='shortlisted').count()
#             rejected = screening_records.filter(admin_decision='not shortlisted').count()
#             data.append({
#                 "service_id": str(service.id),
#                 "service_name": service.name,
#                 "total_proposals": total,
#                 "shortlisted": shortlisted,
#                 "rejected": rejected,
#             })
#         return Response({"screening_status": data})

# class PresentationStatusView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         services = Service.objects.all()
#         data = []
#         for service in services:
#             proposals = FormSubmission.objects.filter(service=service)
#             presentations = Presentation.objects.filter(proposal__in=proposals)
#             total = presentations.count()
#             shortlisted = presentations.filter(final_decision='shortlisted').count()
#             rejected = presentations.filter(final_decision='rejected').count()
#             data.append({
#                 "service_id": str(service.id),
#                 "service_name": service.name,
#                 "total_presentations": total,
#                 "shortlisted": shortlisted,
#                 "rejected": rejected,
#             })
#         return Response({"presentation_status": data})

# class LatestMilestonesView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         proposals = FormSubmission.objects.all()
#         milestone_subq = Milestone.objects.filter(proposal=OuterRef('pk')).order_by('-created_at')
#         submilestone_subq = SubMilestone.objects.filter(milestone__proposal=OuterRef('pk')).order_by('-created_at')
#         proposals_qs = proposals.annotate(
#             latest_milestone_id=Subquery(milestone_subq.values('id')[:1]),
#             latest_milestone_title=Subquery(milestone_subq.values('title')[:1]),
#             latest_milestone_created=Subquery(milestone_subq.values('created_at')[:1]),
#             latest_submilestone_id=Subquery(submilestone_subq.values('id')[:1]),
#             latest_submilestone_title=Subquery(submilestone_subq.values('title')[:1]),
#             latest_submilestone_created=Subquery(submilestone_subq.values('created_at')[:1]),
#         )
#         latest_milestones = {}
#         for proposal in proposals_qs:
#             latest_milestones[proposal.proposal_id or str(proposal.id)] = {
#                 "milestone": {
#                     "id": str(proposal.latest_milestone_id) if proposal.latest_milestone_id else None,
#                     "title": proposal.latest_milestone_title,
#                     "created_at": proposal.latest_milestone_created,
#                 } if proposal.latest_milestone_id else None,
#                 "submilestone": {
#                     "id": str(proposal.latest_submilestone_id) if proposal.latest_submilestone_id else None,
#                     "title": proposal.latest_submilestone_title,
#                     "created_at": proposal.latest_submilestone_created,
#                 } if proposal.latest_submilestone_id else None,
#             }
#         return Response({"latest_milestones": latest_milestones})

# Services wise API
class UserServiceSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        services_summary = [
            {
                "service_id": str(service.id),
                "service_name": service.name,
                "status": service.status,
            }
            for service in services
        ]
        return Response({
            "users": {
                "total": User.objects.count(),
                "active": User.objects.filter(is_active=True).count(),
            },
            "services": {
                "total": services.count(),
                "active": services.filter(status="active").count(),
                "draft": services.filter(status="draft").count(),
                "services_summary": services_summary,
            },
        })
    
class TRLGrowthView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        results = []
        for service in services:
            trl_counts = (
                FormSubmission.objects
                .filter(service=service)
                .exclude(current_trl__isnull=True)
                .values('current_trl')
                .annotate(count=Count('id'))
                .order_by('current_trl')
            )
            results.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "trl_growth": {str(row["current_trl"]): row["count"] for row in trl_counts},
            })
        return Response(results)
    
class ConsensusTRLAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        result = []
        for service in services:
            # Get all TRLAnalysis objects for this service via proposal → technical evaluation round → trl analysis
            proposal_ids = FormSubmission.objects.filter(service=service).values_list('id', flat=True)
            trl_analyses = (
                TRLAnalysis.objects
                .filter(evaluation_round__proposal_id__in=proposal_ids)
                .exclude(consensus_current_trl__isnull=True)
            )
            # Build count for each TRL value (1 to 9)
            trl_counts = {str(i): 0 for i in range(1, 10)}
            for i in range(1, 10):
                trl_counts[str(i)] = trl_analyses.filter(consensus_current_trl=i).count()
            result.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "trl_consensus_counts": trl_counts
            })
        return Response(result)
    
class ScreeningStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        data = []
        for service in services:
            proposals = FormSubmission.objects.filter(service=service)
            records = ScreeningRecord.objects.filter(proposal__in=proposals)
            data.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "total_proposals": proposals.count(),
                "shortlisted": records.filter(admin_decision='shortlisted').count(),
                "rejected": records.filter(admin_decision='not shortlisted').count(),
            })
        return Response(data)       

class PresentationStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        data = []
        for service in services:
            proposals = FormSubmission.objects.filter(service=service)
            presentations = Presentation.objects.filter(proposal__in=proposals)
            data.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "total_presentations": presentations.count(),
                "shortlisted": presentations.filter(final_decision='shortlisted').count(),
                "rejected": presentations.filter(final_decision='rejected').count(),
            })
        return Response(data)         
    
class LatestMilestonesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        result = []
        for service in services:
            proposals = FormSubmission.objects.filter(service=service)
            # Annotate latest milestone & submilestone for each proposal using subquery (fast)
            milestone_subq = Milestone.objects.filter(proposal=OuterRef('pk')).order_by('-created_at')
            submilestone_subq = SubMilestone.objects.filter(milestone__proposal=OuterRef('pk')).order_by('-created_at')

            proposal_qs = proposals.annotate(
                latest_milestone_id=Subquery(milestone_subq.values('id')[:1]),
                latest_milestone_title=Subquery(milestone_subq.values('title')[:1]),
                latest_milestone_created=Subquery(milestone_subq.values('created_at')[:1]),
                latest_submilestone_id=Subquery(submilestone_subq.values('id')[:1]),
                latest_submilestone_title=Subquery(submilestone_subq.values('title')[:1]),
                latest_submilestone_created=Subquery(submilestone_subq.values('created_at')[:1]),
            )
            proposals_data = []
            for proposal in proposal_qs:
                proposals_data.append({
                    "proposal_id": proposal.proposal_id or str(proposal.id),
                    "milestone": {
                        "id": str(proposal.latest_milestone_id) if proposal.latest_milestone_id else None,
                        "title": proposal.latest_milestone_title,
                        "created_at": proposal.latest_milestone_created,
                    } if proposal.latest_milestone_id else None,
                    "submilestone": {
                        "id": str(proposal.latest_submilestone_id) if proposal.latest_submilestone_id else None,
                        "title": proposal.latest_submilestone_title,
                        "created_at": proposal.latest_submilestone_created,
                    } if proposal.latest_submilestone_id else None,
                })
            result.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "proposals": proposals_data,
            })
        return Response(result)

class TechnicalScreeningStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        data = []
        for service in services:
            proposals = FormSubmission.objects.filter(service=service)
            screening_records = ScreeningRecord.objects.filter(proposal__in=proposals)
            tech_records = TechnicalScreeningRecord.objects.filter(screening_record__in=screening_records)
            data.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "total_proposals": proposals.count(),
                "technical_screening_count": tech_records.count(),
                "shortlisted": tech_records.filter(technical_decision='shortlisted').count(),
                "rejected": tech_records.filter(technical_decision='not shortlisted').count(),
            })
        return Response(data)
    
class TechnicalScreeningStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        data = []
        for service in services:
            proposals = FormSubmission.objects.filter(service=service)
            screening_records = ScreeningRecord.objects.filter(proposal__in=proposals)
            tech_records = TechnicalScreeningRecord.objects.filter(screening_record__in=screening_records)
            data.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "total_proposals": proposals.count(),
                "technical_screening_count": tech_records.count(),
                "shortlisted": tech_records.filter(technical_decision='shortlisted').count(),
                "rejected": tech_records.filter(technical_decision='not shortlisted').count(),
            })
        return Response(data)    

class TechnicalEvaluationStatusView(APIView): 
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        services = Service.objects.all()
        data = []
        for service in services:
            proposals = FormSubmission.objects.filter(service=service)
            eval_rounds = TechnicalEvaluationRound.objects.filter(proposal__in=proposals)
            # Shortlisted Presentations for this service
            presentations_shortlisted = Presentation.objects.filter(
                proposal__in=proposals, final_decision='shortlisted'
            ).count()
            data.append({
                "service_id": str(service.id),
                "service_name": service.name,
                "total_proposals": proposals.count(),
                "technical_evaluations": eval_rounds.count(),
                "under_evaluation": eval_rounds.filter(overall_decision='pending').count(),
                "recommended": eval_rounds.filter(overall_decision='recommended').count(),
                "not_recommended": eval_rounds.filter(overall_decision='not_recommended').count(),
                "shortlisted": presentations_shortlisted,
            })
        return Response(data)