"""
URL configuration for auth_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from rest_framework_simplejwt.views import (TokenObtainPairView,TokenRefreshView,)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/dashboard/', include('dashboard.urls')),
        
    path('api/proposal/', include('proposal_aggregate.api.urls')),  
    

    path('api/audit/', include('audit.urls')),
    path('api/auth/', include('users.urls')), 
    path('accounts/', include('allauth.urls')),  # django-allauth
    
    path('api/dynamic-forms/', include('dynamic_form.urls')),    
    
    path('api/config/', include('configuration.urls')),
    path('api/milestones/', include('milestones.urls')),
    path('api/eval/', include('app_eval.urls')),
    path('api/tech-eval/', include('tech_eval.urls')),
 
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
   
    path('api/notifications/', include('notifications.urls')),
    path('api/screening/', include('screening.urls')),
    path('api/presentations/', include('presentation.urls')),
    # path('api/api/', include('api.urls')),
    
    path('api/applicant-dashboard/', include('applicant_dashboard.urls')),
    path('api/form-sections/', include('dynamic_form.form_urls')),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)