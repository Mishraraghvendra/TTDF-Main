# applicant_dashboard/apps.py
from django.apps import AppConfig


class ApplicantDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applicant_dashboard'

    def ready(self):
        import applicant_dashboard.signals