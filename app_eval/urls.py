# app_eval/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EvaluationItemViewSet, EvaluationItemCreateView,
    CriteriaTypeViewSet, FormSubmissionViewSet, EvaluatorViewSet,
    EvaluationAssignmentViewSet, CriteriaEvaluationViewSet,
    QuestionEvaluationViewSet, EvaluationCutoffViewSet,
    TechnicalEvaluationListView, FormSubmissionSearchView,PassingRequirementViewSet,
    TechnicalEvaluationDashboardViewSet,EvaluateProposalViewSet,AssignEvaluatorViewSet,CriteriaListView
)

router = DefaultRouter()
router.register(r'criteria-types', CriteriaTypeViewSet)
router.register(r'form-submissions', FormSubmissionViewSet)
router.register(r'evaluators', EvaluatorViewSet, basename='evaluator')
router.register(r'evaluation-items', EvaluationItemViewSet)
router.register(r'evaluation-assignments', EvaluationAssignmentViewSet)
router.register(r'criteria-evaluations', CriteriaEvaluationViewSet)
router.register(r'question-evaluations', QuestionEvaluationViewSet)
router.register(r'evaluation-cutoffs', EvaluationCutoffViewSet)
router.register(r'passing-requirements', PassingRequirementViewSet)

router.register(r'assignments', AssignEvaluatorViewSet, basename='assignments')
router.register(r'evaluation', TechnicalEvaluationDashboardViewSet, basename='evaluation')
router.register(r'eval',EvaluateProposalViewSet,basename='technical-evaluation')


urlpatterns = [
    path('', include(router.urls)),
    path('criteria-question/create/', EvaluationItemCreateView.as_view(), name='criteria-question-create'),
    path('technical-evaluations/', TechnicalEvaluationListView.as_view(), name='technical-evaluations'),
    path('form-submission-search/', FormSubmissionSearchView.as_view(), name='form-submission-search'),
    # path('evaluate/', EvaluateProposalViewSet.as_view({'post': 'evaluate'})),
    path('criteria-items/', CriteriaListView.as_view(), name='criteria-list'),
]