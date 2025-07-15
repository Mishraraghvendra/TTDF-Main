# dynamic_form/form_urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .form_views import (
    BasicDetailsViewSet, ConsortiumPartnerViewSet, ProposalDetailsViewSet,
    FundDetailsViewSet, BudgetEstimateViewSet, FinanceDetailsViewSet,
    ObjectiveTimelineViewSet, IPRDetailsViewSet, ProjectDetailsViewSet,
    DeclarationViewSet, FormSubmissionControlViewSet
)

# Create router for form sections
router = DefaultRouter()

# Register all form section viewsets
router.register(r'basic-details', BasicDetailsViewSet, basename='basic-details')
router.register(r'consortium-partners', ConsortiumPartnerViewSet, basename='consortium-partners')
router.register(r'proposal-details', ProposalDetailsViewSet, basename='proposal-details')
router.register(r'fund-details', FundDetailsViewSet, basename='fund-details')
router.register(r'budget-estimate', BudgetEstimateViewSet, basename='budget-estimate')
router.register(r'finance-details', FinanceDetailsViewSet, basename='finance-details')
router.register(r'objective-timeline', ObjectiveTimelineViewSet, basename='objective-timeline')
router.register(r'ipr-details', IPRDetailsViewSet, basename='ipr-details')
router.register(r'project-details', ProjectDetailsViewSet, basename='project-details')
router.register(r'declaration', DeclarationViewSet, basename='declaration')
router.register(r'submission-control', FormSubmissionControlViewSet, basename='submission-control')

urlpatterns = [
    path('', include(router.urls)),
]