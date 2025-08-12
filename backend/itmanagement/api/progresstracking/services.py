from datetime import date, timedelta
from django.db.models import Sum, Count, Q
from django.core.cache import cache
from api.dailytask.models import DailyTask, TaskTimeLog, TaskDependency
from api.projects.models import Milestone

def _get_task_logged_hours(task) -> float:
    try:
        logs = TaskTimeLog.objects.filter(task=task)
        total = logs.aggregate(total=Sum("hours"))["total"] or 0
        return float(total)
    except Exception:
        return float(getattr(task, "logged_hours", 0.0) or 0.0)

def burndown_series(project_id: int, days: int = 30) -> list[dict]:
    """
    Returns a list of dicts: {"date": iso, "remaining_hours": float}
    Caches result for 5 minutes to improve performance.
    """
    cache_key = f"burndown_series_{project_id}_{days}"
    result = cache.get(cache_key)
    if result is not None:
        return result

    today = date.today()
    start = today - timedelta(days=days - 1)
    tasks = DailyTask.objects.filter(project_id=project_id)
    remaining_total = 0.0
    for t in tasks:
        est = getattr(t, "estimated_hours", 0) or 0
        logged = _get_task_logged_hours(t)
        remaining = max(float(est) - logged, 0)
        remaining_total += remaining

    series = [{"date": (start + timedelta(days=i)).isoformat(), "remaining_hours": remaining_total} for i in range(days)]
    cache.set(cache_key, series, 300)
    return series

def gantt_payload(project_id: int) -> dict:
    tasks_qs = DailyTask.objects.filter(project_id=project_id).select_related("assigned_to", "sprint")
    tasks = []
    for t in tasks_qs:
        try:
            deps_qs = TaskDependency.objects.filter(task=t)
            deps = [d.depends_on_id for d in deps_qs]
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
    milestones = [{
        "id": m.id,
        "name": getattr(m, "name", getattr(m, "title", "")),
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "end_date": m.end_date.isoformat() if m.end_date else None,
    } for m in milestones_qs]

    return {"tasks": tasks, "milestones": milestones}

def performance_metrics(project_id: int) -> dict:
    qs = DailyTask.objects.filter(project_id=project_id)
    total = qs.count()
    try:
        done_filter = Q(status=DailyTask.Status.DONE)
    except Exception:
        done_filter = Q(status__iexact="done")
    completed = qs.filter(done_filter).count()
    completion_rate = (completed / total) if total else 0

    total_logged = sum(_get_task_logged_hours(t) for t in qs)

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
