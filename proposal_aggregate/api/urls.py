# proposal_aggregate/api/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import ProposalDetailViewSet

router = DefaultRouter()
router.register(r'proposals', ProposalDetailViewSet, basename='proposal-detail')

urlpatterns = [
    path('', include(router.urls)),
]
