from datetime import date, timedelta
from django.db.models import Sum, Count, Q
from django.conf import settings
import os
from dailytask.models import DailyTask, TaskTimeLog  ,TaskDependency
from projects.models import Milestone 

def _get_task_logged_hours(task):
    """
    Compute logged hours for a DailyTask by summing TaskTimeLog if model exists,
    otherwise look for attribute 'logged_hours' on the task.
    """
    try:
        # If TaskTimeLog model exists and references DailyTask via 'task' FK and has 'hours' field
        logs = TaskTimeLog.objects.filter(task=task)
        total = logs.aggregate(total=Sum("hours"))["total"] or 0
        return float(total)
    except Exception:
        # fallback to attribute on model
        return float(getattr(task, "logged_hours", 0.0) or 0.0)

def burndown_series(project_id, days=30):
    """
    Returns a list of dicts: {"date": iso, "remaining_hours": float}
    This uses a current-snapshot approach: remaining hours are computed from current task estimates/logs.
    If you want historical burndown, schedule daily snapshots and return those values instead.
    """
    today = date.today()
    start = today - timedelta(days=days - 1)
    tasks = DailyTask.objects.filter(project_id=project_id)
    # estimate field may not exist; handle gracefully
    remaining_total = 0.0
    for t in tasks:
        est = getattr(t, "estimated_hours", None)
        logged = _get_task_logged_hours(t)
        try:
            est_f = float(est) if est is not None else 0.0
        except Exception:
            est_f = 0.0
        if est_f - logged > 0:
            remaining_total += (est_f - logged)
    # Return same snapshot for each day (pragmatic)
    series = []
    for i in range(days):
        d = start + timedelta(days=i)
        series.append({"date": d.isoformat(), "remaining_hours": remaining_total})
    return series

def gantt_payload(project_id):
    """
    Return tasks and milestones in a frontend-friendly structure:
    - tasks: list of {id, title, start_date, end_date, assignee, status, dependencies}
    - milestones: list of {id, name, start_date, end_date}
    """
    tasks_qs = DailyTask.objects.filter(project_id=project_id).select_related("assigned_to", "sprint")
    tasks = []
    for t in tasks_qs:
        # Determine dependencies if you have TaskDependency model; adapt if names differ
        deps = []
        try:
            # Many projects store dependencies in a model TaskDependency with fields task / depends_on
            deps_qs = getattr(t, "dependencies", None)
            if deps_qs is None:
                # maybe there is a separate model TaskDependency with task field
                deps_qs = TaskDependency.objects.filter(task=t)
                deps = [d.depends_on_id for d in deps_qs]
            else:
                deps = [d.id for d in deps_qs.all()]
        except Exception:
            deps = []

        tasks.append({
            "id": t.id,
            "title": getattr(t, "title", getattr(t, "name", "")),
            "start_date": getattr(t, "start_date", None).isoformat() if getattr(t, "start_date", None) else None,
            "end_date": getattr(t, "due_date", None).isoformat() if getattr(t, "due_date", None) else None,
            "assignee": getattr(getattr(t, "assigned_to", None), "username", None),
            "status": getattr(t, "status", None),
            "priority": getattr(t, "priority", None),
            "dependencies": deps,
        })

    milestones_qs = Milestone.objects.filter(project_id=project_id)
    milestones = []
    for m in milestones_qs:
        milestones.append({
            "id": m.id,
            "name": getattr(m, "name", getattr(m, "title", "")),
            "start_date": m.start_date.isoformat() if m.start_date else None,
            "end_date": m.end_date.isoformat() if m.end_date else None,
        })

    return {"tasks": tasks, "milestones": milestones}

def performance_metrics(project_id):
    """
    Returns: total_tasks, completed_tasks, completion_rate, total_logged_hours, by_user list.
    """
    qs = DailyTask.objects.filter(project_id=project_id)
    total = qs.count()
    # status values may be enums; we check for 'Done' / 'DONE' / 'done' and also try DailyTask.Status if exists
    try:
        done_filter = Q(status=DailyTask.Status.DONE)  # if TextChoices exists
    except Exception:
        done_filter = Q(status__iexact="done")
    completed = qs.filter(done_filter).count()
    completion_rate = (completed / total) if total else 0

    # total logged hours from logs or attribute
    total_logged = 0.0
    for t in qs:
        total_logged += _get_task_logged_hours(t)

    # by_user aggregated
    by_user_qs = qs.values("assigned_to__id", "assigned_to__username").annotate(
        total_tasks=Count("id"),
        completed=Count("id", filter=done_filter)
    )
    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "completion_rate": completion_rate,
        "total_logged_hours": float(total_logged),
        "by_user": list(by_user_qs),
    }

def ensure_report_dir():
    """
    Ensure MEDIA_ROOT/progress_reports exists and return absolute path
    """
    base = getattr(settings, "MEDIA_ROOT", None)
    if not base:
        raise RuntimeError("MEDIA_ROOT not set in settings")
    out_dir = os.path.join(base, "progress_reports")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir
