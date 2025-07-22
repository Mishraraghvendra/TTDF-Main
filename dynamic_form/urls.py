from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dynamic_form import views as forms_views
from django.conf import settings
from django.conf.urls.static import static

from .views import FormTemplateViewSet, FormSubmissionViewSet,ProposalVillageStatsAPIView

router = DefaultRouter()
router.register(r'templates',   FormTemplateViewSet,    basename='template')
router.register(r'submissions', FormSubmissionViewSet,  basename='submission')

urlpatterns = [
    path('', include(router.urls)),
    path('form-sections/', include('dynamic_form.form_urls')),
    path('proposals/village-stats/', ProposalVillageStatsAPIView.as_view(), name='proposal-village-stats'),
]
    

# Add media file serving for development environment
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)