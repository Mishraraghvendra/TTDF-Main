# tech_eval/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TechnicalEvaluationRoundViewSet,
    EvaluatorAssignmentViewSet,
    CriteriaEvaluationViewSet, EvaluationCriteriaViewSet,EvaluatorListView
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'technical-evaluations', TechnicalEvaluationRoundViewSet, basename='technical-evaluations')
router.register(r'evaluator-assignments', EvaluatorAssignmentViewSet, basename='evaluator-assignments')
router.register(r'criteria-evaluations', CriteriaEvaluationViewSet, basename='criteria-evaluations')
router.register(r'evaluation-criteria', EvaluationCriteriaViewSet, basename='evaluation-criteria')

# URL patterns
urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    path('evaluators/', EvaluatorListView.as_view(), name='evaluator-list'),
]