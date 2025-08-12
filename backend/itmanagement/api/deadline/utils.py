from collections import deque
from django.utils import timezone
from django.db import transaction
from dailytask.models import DailyTask
from dailytask.models import TaskDependency  
from django.conf import settings
import datetime
import logging

logger = logging.getLogger(__name__)

WORKING_HOURS_PER_DAY = getattr(settings, "WORKING_HOURS_PER_DAY", 8)

def compute_critical_path(project_id, override_task_durations=None):
    tasks = list(DailyTask.objects.filter(project_id=project_id))
    if not tasks:
        return {"duration_hours": 0.0, "path_task_ids": []}

    tmap = {t.id: t for t in tasks}
    indeg = {t.id: 0 for t in tasks}
    adj = {t.id: [] for t in tasks}

    for t in tasks:
        # Gather dependencies for each task
        deps = []
        if hasattr(t, "dependencies"):
            deps = [d.id for d in t.dependencies.all()]
        else:
            try:
                deps = [dep.depends_on_id for dep in TaskDependency.objects.filter(task=t)]
            except Exception:
                deps = []

        indeg[t.id] = len(deps)
        for dep_id in deps:
            adj.setdefault(dep_id, []).append(t.id)

    q = deque([tid for tid, d in indeg.items() if d == 0])
    longest = {tid: (0.0, [tid]) for tid in indeg}
    while q:
        u = q.popleft()
        dur_u, path_u = longest[u]

        # Use override duration if provided
        est_u = override_task_durations.get(u) if override_task_durations and u in override_task_durations else float(getattr(tmap[u], "estimated_hours", 0) or 0)

        total_u = dur_u + est_u
        for v in adj.get(u, []):
            curr_dur, curr_path = longest.get(v, (0.0, []))
            if total_u > curr_dur:
                longest[v] = (total_u, path_u + [v])
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)

    best = max(longest.items(), key=lambda kv: kv[1][0])
    duration, path = best[1][0], best[1][1]
    return {"duration_hours": duration, "path_task_ids": path}


def deadline_impact_assessment(task_id, delay_days):
    try:
        t = DailyTask.objects.get(id=task_id)
    except DailyTask.DoesNotExist:
        return {"error": "Task not found"}

    project_id = t.project_id
    original = compute_critical_path(project_id)

    added_hours = float(delay_days) * WORKING_HOURS_PER_DAY
    orig_est = float(getattr(t, "estimated_hours", 0) or 0)

    override_durations = {task_id: orig_est + added_hours}

    new = compute_critical_path(project_id, override_task_durations=override_durations)

    shift = new["duration_hours"] - original["duration_hours"]

    return {
        "project_id": project_id,
        "task_id": task_id,
        "original_duration_hours": original["duration_hours"],
        "new_duration_hours": new["duration_hours"],
        "shift_hours": shift,
        "shift_days": shift / WORKING_HOURS_PER_DAY if WORKING_HOURS_PER_DAY else None,
        "original_path": original.get("path_task_ids", []),
        "new_path": new.get("path_task_ids", []),
    }


def adjust_task_timeline(task_id, new_start=None, new_due=None):
    """
    Update task start and due dates and adjust dependent tasks' start dates accordingly.
    Returns changed info and list of impacted dependent task IDs.
    """
    try:
        t = DailyTask.objects.get(id=task_id)
    except DailyTask.DoesNotExist:
        return {"error": "Task not found"}

    changed = {}
    if new_start:
        t.start_date = new_start
        changed["start_date"] = new_start.isoformat()
    if new_due:
        t.due_date = new_due
        changed["due_date"] = new_due.isoformat()
    t.save()

    dependents = []
    if hasattr(t, "dependents"):
        dependents = list(t.dependents.all())
    else:
        try:
            dependents = list(TaskDependency.objects.filter(depends_on=t).values_list("task", flat=True))
            dependents = DailyTask.objects.filter(id__in=dependents)
        except Exception:
            dependents = []

    impacted_ids = []
    for dep in dependents:
        impacted_ids.append(dep.id)
        if new_due and dep.start_date and dep.start_date < new_due:
            dep.start_date = new_due
            dep.save()

    return {"task_id": task_id, "changed": changed, "dependents_impacted": impacted_ids}


def _create_notifications(project_id, task_id=None, milestone_id=None, sprint_id=None, due_date=None):
    """
    Create DeadlineNotification instances for given due date and configured reminder offsets.
    """
    if not due_date:
        return []

    from django.utils import timezone
    from .models import DeadlineNotification
    from django.conf import settings

    DEFAULT_REMINDER_OFFSETS = getattr(settings, "DEADLINE_REMINDER_OFFSETS_DAYS", [2, 1])
    now = timezone.now()
    created_notifications = []

    for offset in DEFAULT_REMINDER_OFFSETS:
        notify_dt = datetime.datetime.combine(due_date, datetime.time(hour=9))
        if timezone.is_naive(notify_dt):
            notify_dt = timezone.make_aware(notify_dt)
        notify_dt -= datetime.timedelta(days=offset)
        if notify_dt > now:
            notif = DeadlineNotification(
                project_id=project_id,
                task_id=task_id,
                milestone_id=milestone_id,
                sprint_id=sprint_id,
                notify_at=notify_dt,
                escalation=False
            )
            notif.save()
            created_notifications.append(notif)

    return created_notifications
