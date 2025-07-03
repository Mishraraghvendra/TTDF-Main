from django.urls import path
from .views import AdminDashboardSummaryView,EvaluatorDashboardView

from .views import (
    UserServiceSummaryView, TRLGrowthView, ScreeningStatusView,
    PresentationStatusView, LatestMilestonesView,TechnicalScreeningStatusView, TechnicalEvaluationStatusView,ConsensusTRLAnalysisView
)
from .views_ia import (IADashboardAPIView,AllServicesAPIView,DocumentStatusCountAPIView,IASummaryAPIView,IAUtilizationOverviewAPIView,
    IAProposalTrackerAPIView, IAMilestoneStatusAPIView,
    IAProposalFinancialStatusAPIView,IAServiceWiseDashboardAPIView,IAServiceSummaryAPIView,
    IAServiceUtilizationAPIView,
    IAServiceProposalsAPIView,
    IAServiceMilestoneClaimsAPIView,MultipleProposalsAPIView)

from .views_super_admin import PermissionManagementAPIView,RolePermissionsAPIView

urlpatterns = [
    path('admin-summary/', AdminDashboardSummaryView.as_view(), name='admin-dashboard-summary'),
    path('evaluator-summary/', EvaluatorDashboardView.as_view(), name='evaluator-dashboard'),


    path('user-service-summary/', UserServiceSummaryView.as_view()),
    path('trl-growth/', TRLGrowthView.as_view()),
    path('Consensus-trl/',  ConsensusTRLAnalysisView.as_view()),
    path('screening-status/', ScreeningStatusView.as_view()),
    path('technical-screening-status/', TechnicalScreeningStatusView.as_view()),
    path('presentation-status/', PresentationStatusView.as_view()),
    path('technical-evaluation-status/', TechnicalEvaluationStatusView.as_view()),
    path('latest-milestones/', LatestMilestonesView.as_view()),



    path('all-services/', AllServicesAPIView.as_view(), name='all-services'),
    path('ia-dashboard/', IADashboardAPIView.as_view(), name='ia-dashboard'),
    path('doc-counts/', DocumentStatusCountAPIView.as_view(), name='service-doc-status-counts'),
    path('ia-dashboard/summary/', IASummaryAPIView.as_view()),
    path('ia-dashboard/utilization/', IAUtilizationOverviewAPIView.as_view()),
    path('ia-dashboard/proposals/', IAProposalTrackerAPIView.as_view()),
    path('ia-dashboard/milestone-status/', IAMilestoneStatusAPIView.as_view()),
    path('ia-dashboard/financial-status/', IAProposalFinancialStatusAPIView.as_view()),



    path('ia-dashboard/services-summary/', IAServiceWiseDashboardAPIView.as_view()),

    path('ia-dashboard/services-summary/', IAServiceSummaryAPIView.as_view()),
    path('ia-dashboard/services-utilization/', IAServiceUtilizationAPIView.as_view()),
    path('ia-dashboard/services-proposals/', IAServiceProposalsAPIView.as_view()),
    path('ia-dashboard/services-milestone-claims/', IAServiceMilestoneClaimsAPIView.as_view()), 



     path('multiple-proposals/', MultipleProposalsAPIView.as_view(), name='multiple-proposals'),

     path('permissions/', PermissionManagementAPIView.as_view(), name='permissions-management'),
     path('role-permissions/', RolePermissionsAPIView.as_view(), name='role-permissions'),
    
    

]