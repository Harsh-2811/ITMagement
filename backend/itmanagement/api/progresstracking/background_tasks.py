import datetime
import uuid
import os
import csv
from django.conf import settings
from background_task import background
from django.utils import timezone
from django.core.files import File
from django.contrib.auth import get_user_model

from .models import ProgressReport
from .utils import burndown_series, gantt_payload, performance_metrics, ensure_report_dir
from api.dailytask.models import DailyTask
from api.projects.models import Project

User = get_user_model()


def make_json_safe(obj):
    """Recursively convert UUIDs, datetimes, and unsupported types to JSON-safe."""
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif hasattr(obj, "_meta"):  
        return str(obj.pk)
    else:
        return obj


@background(schedule=5)
def generate_progress_report(project_id, user_id=None):
    """Generate JSON analytics and CSV report for a project."""
    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        return None

    data = {
        "burndown": burndown_series(project_id, days=30),
        "gantt": gantt_payload(project_id),
        "metrics": performance_metrics(project_id)
    }
    data = make_json_safe(data)

    # Get user object
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass

    # Create the report first
    report = ProgressReport.objects.create(
        project_id=project_id,
        generated_by=user,
        report_data=data,
    )

    # Generate CSV
    try:
        out_dir = ensure_report_dir() 
        ts = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"progress_report_{project.project_id}_{ts}.csv"
        filepath = os.path.join(out_dir, filename)

        tasks = DailyTask.objects.filter(project_id=project_id).select_related("assigned_to", "sprint")
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                "Task ID", "Title", "Assignee", "Status", "Priority", "Category",
                "Estimated Hours", "Logged Hours", "Remaining Hours", "Start Date", "Due Date"
            ])
            for t in tasks:
                est = getattr(t, "estimated_hours", "")
                try:
                    from .utils import _get_task_logged_hours
                    logged = _get_task_logged_hours(t)
                except Exception:
                    logged = getattr(t, "logged_hours", "")
                try:
                    remaining = (float(est) - float(logged)) if est and logged else ""
                except Exception:
                    remaining = ""
                writer.writerow([
                    t.id,
                    getattr(t, "title", getattr(t, "name", "")),
                    getattr(getattr(t, "assigned_to", None), "username", ""),
                    getattr(t, "status", ""),
                    getattr(t, "priority", ""),
                    getattr(t, "category", ""),
                    est,
                    logged,
                    remaining,
                    t.start_date.isoformat() if getattr(t, "start_date", None) else "",
                    t.due_date.isoformat() if getattr(t, "due_date", None) else "",
                ])
    except Exception as e:
        filepath = None

    # Save the CSV to FileField **after report is created**
    if filepath and os.path.exists(filepath):
        with open(filepath, "rb") as f:
            report.csv_file.save(os.path.basename(filepath), File(f), save=True)

    # Force save to make sure DB column is updated
    report.save()

    return report.id
