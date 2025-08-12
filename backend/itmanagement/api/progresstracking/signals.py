from django.db.models.signals import post_save
from django.dispatch import receiver
from api.dailytask.models import DailyTask
from api.projects.models import Milestone  
import django_eventstream
from .background_tasks import generate_progress_report

@receiver(post_save, sender=DailyTask)
def push_task_update(sender, instance, **kwargs):
    channel = f'project-{instance.project.id}'
    django_eventstream.send_event(
        channel,                     # first positional arg: channel
        'task_update',               # second positional arg: event_type
        data={
            'task_id': instance.id,
            'task_name': instance.title,
            'progress': instance.status,
            'updated_at': instance.updated_at.isoformat(),
        }
    )
@receiver(post_save, sender=DailyTask)
def on_daily_task_save(sender, instance, created, **kwargs):
    """
    When a DailyTask changes, schedule a quick progress report generation.
    Using schedule=0 will enqueue immediately (if worker running).
    """
    project_id = getattr(instance, "project_id", None)
    if project_id:
        # attempt to pass the project owner as user if available; otherwise None
        try:
            owner = instance.project.created_by.id
        except Exception:
            owner = None
        # schedule background generation immediately (use schedule=0)
        generate_progress_report(project_id, owner, schedule=0)

@receiver(post_save, sender=Milestone)
def on_milestone_save(sender, instance, created, **kwargs):
    project_id = getattr(instance, "project_id", None)
    if project_id:
        try:
            owner = instance.project.created_by.id
        except Exception:
            owner = None
        generate_progress_report(project_id, owner, schedule=0)
