from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import datetime
from projects.models import DeadlineNotification
from dailytask.models import DailyTask
from projects.models import Milestone
from sprints.models import Sprint 
from .tasks import process_deadline_notifications
from django.conf import settings


DEFAULT_REMINDER_OFFSETS = getattr(settings, "DEADLINE_REMINDER_OFFSETS_DAYS", [2, 1])

def _create_notifications(project_id, task_id=None, milestone_id=None, sprint_id=None, due_date=None):
    """
    Generic notification creator for tasks, milestones, and sprints.
    """
    if not due_date:
        return

    now = timezone.now()
    for offset in DEFAULT_REMINDER_OFFSETS:
        notify_dt = datetime.datetime.combine(due_date, datetime.time(hour=9)) - datetime.timedelta(days=offset)
        if timezone.is_naive(notify_dt):
            notify_dt = timezone.make_aware(notify_dt)
        if notify_dt > now:
            DeadlineNotification.objects.create(
                project_id=project_id,
                task_id=task_id,
                milestone_id=milestone_id,
                sprint_id=sprint_id,
                notify_at=notify_dt,
                escalation=False
            )

@receiver(post_save, sender=DailyTask)
def on_task_save(sender, instance, created, **kwargs):
    DeadlineNotification.objects.filter(task_id=instance.id, sent=False).delete()
    _create_notifications(project_id=instance.project_id, task_id=instance.id, due_date=instance.due_date)
    process_deadline_notifications(schedule=0)

@receiver(post_save, sender=Milestone)
def on_milestone_save(sender, instance, created, **kwargs):
    DeadlineNotification.objects.filter(milestone_id=instance.id, sent=False).delete()
    _create_notifications(project_id=instance.project_id, milestone_id=instance.id, due_date=instance.end_date)
    process_deadline_notifications(schedule=0)

@receiver(post_save, sender=Sprint)
def on_sprint_save(sender, instance, created, **kwargs):
    DeadlineNotification.objects.filter(sprint_id=instance.id, sent=False).delete()
    _create_notifications(project_id=instance.project_id, sprint_id=instance.id, due_date=instance.end_date)
    process_deadline_notifications(schedule=0)
