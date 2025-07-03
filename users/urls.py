from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    RegisterApplicantView,
    LoginView,
    ProfileView,
    RoleViewSet,
    AccountUserViewSet,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    AssignRoleView, AssignPermissionView,ChangeUserRoleView,EvaluatorUserListAPIView,
    InitialSignupView,GetProfileView,UpdateProfileView,ProfileStatusView,
    SubmissionDetailView,AllSubmissionsView
)

router = DefaultRouter()
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'users', AccountUserViewSet, basename='user')

urlpatterns = [
    path('signup/', RegisterApplicantView.as_view(), name='signup'),
    path('assign-role/',       AssignRoleView.as_view(),       name='assign-role'),
    path('change-role/', ChangeUserRoleView.as_view(), name='change-role'),
    path('assign-permission/', AssignPermissionView.as_view(), name='assign-permission'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('evaluator-users/', EvaluatorUserListAPIView.as_view(), name='evaluator-users'),
    path('', include(router.urls)),

    path('initial-signup/', InitialSignupView.as_view(), name='initial-signup'),
    path('get-profile/', GetProfileView.as_view(), name='get-profile'),
    path('update-profile/', UpdateProfileView.as_view(), name='update-profile'),
    path('profile-status/', ProfileStatusView.as_view(), name='profile-status'),
    path('submission-detail/', SubmissionDetailView.as_view(), name='submission-detail'),
    path('all-submissions/', AllSubmissionsView.as_view(), name='all-submissions'),
]