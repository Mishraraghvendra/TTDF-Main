from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from .views import (
    DashboardOverviewAPIView,
    ProposalStatsAPIView,
    UserActivityViewSet,
    CallsAPIView,
    ProjectMilestonesAPIView,
    FinanceDataAPIView,
    DocumentUploadAPIView,
    ProposalDetailsAPIView,
    RefreshStatsAPIView
)

router = DefaultRouter()
router.register(r'activities', UserActivityViewSet, basename='activity')

app_name = 'applicant_dashboard'

urlpatterns = [
    path('overview/', DashboardOverviewAPIView.as_view(), name='dashboard-overview'),
    path('proposal-stats/', ProposalStatsAPIView.as_view(), name='proposal-stats'),
    path('calls/', CallsAPIView.as_view(), name='calls-data'),
    path('', include(router.urls)),
    re_path(r'^proposal-details/(?P<proposal_id>[^/]+(?:/[^/]+)*)/$', ProposalDetailsAPIView.as_view(), name='proposal-details'),
    re_path(r'^milestones/(?P<proposal_id>[^/]+(?:/[^/]+)*)/$', ProjectMilestonesAPIView.as_view(), name='project-milestones'),
    re_path(r'^finance/(?P<proposal_id>[^/]+(?:/[^/]+)*)/$', FinanceDataAPIView.as_view(), name='finance-data'),
    path('upload-document/', DocumentUploadAPIView.as_view(), name='upload-document'),
    path('refresh-stats/', RefreshStatsAPIView.as_view(), name='refresh-stats'),
]

