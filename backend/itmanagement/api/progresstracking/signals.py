from django.db.models.signals import post_save
from django.dispatch import receiver
from api.dailytask.models import DailyTask
from api.projects.models import Milestone  
import django_eventstream
from .background_tasks import generate_progress_report


@receiver(post_save, sender=DailyTask)
def push_task_update(sender, instance, **kwargs):
    """Send realtime update event when a DailyTask changes."""
    channel = f'project-{instance.project.id}'
    django_eventstream.send_event(
        channel,
        'task_update',
        data={
            'task_id': instance.id,
            'task_name': instance.title,
            'progress': instance.status,
            'updated_at': instance.updated_at.isoformat(),
        }
    )


@receiver(post_save, sender=DailyTask)
def on_daily_task_save(sender, instance, created, **kwargs):
    """Schedule progress report when a DailyTask changes."""
    project_id = getattr(instance, "project_id", None)
    if project_id:
        try:
            owner = instance.project.created_by.id
        except Exception:
            owner = None
        generate_progress_report(project_id=project_id, user_id=owner, schedule=0)


@receiver(post_save, sender=Milestone)
def on_milestone_save(sender, instance, created, **kwargs):
    """Schedule progress report when a Milestone changes."""
    project_id = getattr(instance, "project_id", None)
    if project_id:
        try:
            owner = instance.project.created_by.id
        except Exception:
            owner = None
        generate_progress_report(project_id=project_id, user_id=owner, schedule=0)
