from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import datetime
import threading
import logging
from .models import DeadlineNotification
from dailytask.models import DailyTask
from projects.models import Milestone
from sprints.models import Sprint
from .utils import _create_notifications

logger = logging.getLogger(__name__)

_notification_lock = threading.Lock()
_last_notification_run = None
_NOTIFICATION_DEBOUNCE_SECONDS = 10

def process_deadline_notifications(schedule=0):
    global _last_notification_run
    now = timezone.now()

    with _notification_lock:
        if _last_notification_run and (now - _last_notification_run).total_seconds() < _NOTIFICATION_DEBOUNCE_SECONDS:
            logger.debug("Skipping notification run due to debounce")
            return
        _last_notification_run = now

    notifications = DeadlineNotification.objects.filter(sent=False, notify_at__lte=now)
    for notif in notifications:
        logger.info(f"Sending notification for {notif}")
        notif.sent = True
        notif.save()

@receiver(post_save, sender=DailyTask)
def on_task_save(sender, instance, created, **kwargs):
    DeadlineNotification.objects.filter(task=instance, sent=False).delete()
    _create_notifications(project_id=instance.project_id, task_id=instance.id, due_date=instance.due_date)
    process_deadline_notifications(schedule=0)

@receiver(post_save, sender=Milestone)
def on_milestone_save(sender, instance, created, **kwargs):
    DeadlineNotification.objects.filter(milestone=instance, sent=False).delete()
    _create_notifications(project_id=instance.project_id, milestone_id=instance.id, due_date=instance.end_date)
    process_deadline_notifications(schedule=0)

@receiver(post_save, sender=Sprint)
def on_sprint_save(sender, instance, created, **kwargs):
    DeadlineNotification.objects.filter(sprint=instance, sent=False).delete()
    _create_notifications(project_id=instance.project_id, sprint_id=instance.id, due_date=instance.end_date)
    process_deadline_notifications(schedule=0)
