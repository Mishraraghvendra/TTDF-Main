# screening/urls.py
from django.urls import path, include,re_path
from rest_framework.routers import DefaultRouter
from .views import ScreeningRecordViewSet, TechnicalScreeningRecordViewSet,AdministrativeScreeningViewSet,TechnicalScreeningDashboardViewSet,AdminScreeningViewSet,AdminTechnicalScreeningViewSet       #,TechnicalEvaluationDashboardViewSet

router = DefaultRouter()
#router.register(r'screeningrecords', ScreeningRecordViewSet, basename='screeningrecord')   
router.register(r'technicalrecords', TechnicalScreeningRecordViewSet, basename='technicalrecord')
router.register(r'administrative', AdministrativeScreeningViewSet, basename='administrative-screening')
router.register(r'technical', TechnicalScreeningDashboardViewSet, basename='technical-screening')
# router.register(r'evaluation', TechnicalEvaluationDashboardViewSet, basename='technical-evaluation')

router.register(r'adminscreening', AdminScreeningViewSet, basename='admin-screening')
router.register(r'admintechnical', AdminTechnicalScreeningViewSet, basename='admin_technical')


urlpatterns = [
    path('', include(router.urls)),

    re_path(
        r'^screeningrecords/(?P<proposal_id>.+)/$',
        ScreeningRecordViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}),
        name='screeningrecord-detail'
    ),

]
