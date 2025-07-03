from django.apps import AppConfig

class UsersConfig(AppConfig):
    name = 'users'
    verbose_name = 'User Management'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Ensure signal handlers are registered
        import users.signals  # noqa: F401