from celery import Celery
from celery.schedules import crontab

app = Celery('project_name')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-invoice-reminders-daily': {
        'task': 'yourapp.tasks.send_invoice_reminders',
        'schedule': crontab(hour=9, minute=0),  # Every day at 9 AM
    },
}
