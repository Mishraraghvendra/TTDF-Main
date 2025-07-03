# milestones/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import upload_milestone_document, raise_payment_claim
from .views import project_tracker_proposal, project_tracker_milestones,project_tracker_milestone_documents, project_tracker_submilestone_documents
from .views import (MilestoneViewSet, SubMilestoneViewSet,FinanceRequestViewSet, PaymentClaimViewSet,IAMilestoneViewSet,SanctionViewSet,
FinanceSanctionViewSet,FinanceViewSet,SubMilestoneDocumentViewSet,MilestoneDocumentViewSet,ProposalMouDocumentViewSet,
ImplementationAgencyViewSet,ShortlistedProposalDetailView,ShortlistedProposalsBasicView)

router = DefaultRouter()

router.register(r'milestones', MilestoneViewSet)
router.register(r'submilestones', SubMilestoneViewSet)
router.register(r'milestone-documents', MilestoneDocumentViewSet)
router.register(r'submilestone-documents', SubMilestoneDocumentViewSet)
router.register(r'proposal-mou-documents', ProposalMouDocumentViewSet)


router.register(r'finance-requests',   FinanceRequestViewSet, basename='finance-request')
router.register(r'payment-claims',     PaymentClaimViewSet,   basename='payment-claim')
router.register(r'sanctions',          FinanceSanctionViewSet,basename='finance-sanction')
router.register(r'IA-milestones',      IAMilestoneViewSet,    basename='IA-milestones')
router.register(r'sanctionsdata',      SanctionViewSet,       basename='sanctions')
router.register(r'iasanctions',        FinanceViewSet,        basename='iasanctions')
router.register(r'ias', ImplementationAgencyViewSet)




urlpatterns = [
    path('', include(router.urls)),

    path('shortlisted-proposals/<path:proposal_id>/', ShortlistedProposalDetailView.as_view(), name='shortlisted-proposal-detail'),
    path('shortlisted-proposals/', ShortlistedProposalsBasicView.as_view(), name='shortlisted-proposals-list'),

    path('project-tracker/proposal/', 
         project_tracker_proposal, 
         name='project-tracker-proposal'),
    
    path('project-tracker/milestones/', 
         project_tracker_milestones, 
         name='project-tracker-milestones'),
    
    path('project-tracker/milestone-documents/', 
         project_tracker_milestone_documents, 
         name='project-tracker-milestone-documents'),
    
    path('project-tracker/submilestone-documents/', 
         project_tracker_submilestone_documents, 
         name='project-tracker-submilestone-documents'),
          # Document Upload and Payment Claim APIs
    path('upload-document/', 
         upload_milestone_document, 
         name='upload-milestone-document'),
    
    path('raise-claim/', 
         raise_payment_claim, 
         name='raise-payment-claim'),
]
 