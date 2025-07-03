# presentation/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PresentationViewSet,PersonalInterviewViewSet

router = DefaultRouter()
router.register(r'presentations', PresentationViewSet, basename='presentation')
router.register(r'personal-interviews', PersonalInterviewViewSet, basename='personal-interview')



urlpatterns = [
    path('', include(router.urls)),
]
