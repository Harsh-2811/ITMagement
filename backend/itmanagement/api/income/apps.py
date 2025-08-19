from django.apps import AppConfig


class IncomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.income'
    def ready(self):
        from . import signals  
