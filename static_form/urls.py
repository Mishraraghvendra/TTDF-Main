from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StaticFormViewSet

router = DefaultRouter()
router.register('forms', StaticFormViewSet, basename='static-form')

urlpatterns = [
    path('', include(router.urls)),
]
