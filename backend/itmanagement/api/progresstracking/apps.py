from django.apps import AppConfig

class ProgressTrackingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.progresstracking'

    def ready(self):
        import api.progresstracking.signals