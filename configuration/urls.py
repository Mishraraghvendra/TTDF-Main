from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from configuration import views as config_views 
from django.conf import settings
from django.conf.urls.static import static
from .views import CommitteeListAPIView,CriteriaListAPIView


config_router = DefaultRouter()
config_router.register(r'users', config_views.UserViewSet)
config_router.register(r'services', config_views.ServiceViewSet)
config_router.register(r'service-forms', config_views.ServiceFormViewSet)
config_router.register(r'evaluation-stages', config_views.EvaluationStageViewSet)
config_router.register(r'evaluation-criteria', config_views.EvaluationCriteriaConfigViewSet)
config_router.register(r'evaluator-assignments', config_views.EvaluatorAssignmentViewSet)
config_router.register(r'applications', config_views.ApplicationViewSet)
config_router.register(r'application-progress', config_views.ApplicationStageProgressViewSet)
config_router.register(r'screening-committees', config_views.ScreeningCommitteeViewSet)
config_router.register(r'committee-members', config_views.CommitteeMemberViewSet)
config_router.register(r'screening-results', config_views.ScreeningResultViewSet)

urlpatterns = [  

    path('', include(config_router.urls)),
    path('committees/', CommitteeListAPIView.as_view(), name='committee-list'),
     path('criteria/', CriteriaListAPIView.as_view(), name='criteria-list'),

]

# Add media file serving for development environment
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)