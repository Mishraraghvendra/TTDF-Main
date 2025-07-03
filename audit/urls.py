from rest_framework import routers
from audit.views import ActivityLogViewSet,AdminUserListView, AdminUserDetailView, AdminActivityLogViewSet,LatestActivityLogsAPIView
from django.urls import path, include

router = routers.DefaultRouter()
router.register(r'audit-logs', ActivityLogViewSet, basename='audit-log')
router.register(r'logs', AdminActivityLogViewSet, basename='log')

urlpatterns = [
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('latest-logs/', LatestActivityLogsAPIView.as_view(), name='latest-logs'),
    path('', include(router.urls)),
]