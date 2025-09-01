import datetime
import uuid
import os
import csv
import logging

from django.conf import settings
from background_task import background
from django.utils import timezone
from django.core.files import File
from django.contrib.auth import get_user_model

from .models import ProgressReport
from .utils import burndown_series, gantt_payload, performance_metrics, ensure_report_dir, _get_task_logged_hours
from api.dailytask.models import DailyTask
from api.projects.models import Project

logger = logging.getLogger(__name__)
User = get_user_model()


def make_json_safe(obj):
    """Recursively convert UUIDs, datetimes, and unsupported types to JSON-safe values."""
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif hasattr(obj, "_meta"):  # Django model instance
        return str(obj.pk)
    return obj


@background(schedule=5)  # runs ~5 seconds after scheduling
def generate_progress_report(project_id, user_id=None):
    """Generate JSON analytics and CSV report for a project."""
    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.error(f"Project {project_id} does not exist.")
        return None

    # Build analytics data
    try:
        data = make_json_safe({
            "burndown": burndown_series(project_id, days=30),
            "gantt": gantt_payload(project_id),
            "metrics": performance_metrics(project_id),
        })
    except Exception as e:
        logger.exception(f"Failed to generate analytics for project {project_id}: {e}")
        return None

    # Get user if provided
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(f"User {user_id} not found. Continuing without user.")

    report = ProgressReport.objects.create(
    project_id=project.id,  
    generated_by=user,
    report_data=data,
)

    filepath = None
    try:
        out_dir = ensure_report_dir()
        ts = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"progress_report_{project.id}_{ts}.csv"
        filepath = os.path.join(out_dir, filename)

        tasks = DailyTask.objects.filter(project=project).select_related("assigned_to", "sprint")

        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                "Task ID", "Title", "Assignee", "Status", "Priority", "Category",
                "Estimated Hours", "Logged Hours", "Remaining Hours", "Start Date", "Due Date"
            ])
            for t in tasks:
                est = getattr(t, "estimated_hours", 0) or 0
                try:
                    logged = _get_task_logged_hours(t) or 0
                except Exception:
                    logged = getattr(t, "logged_hours", 0) or 0

                remaining = ""
                try:
                    remaining = float(est) - float(logged)
                except Exception:
                    pass

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
        logger.exception(f"Failed to generate CSV for project {project_id}: {e}")
        filepath = None

    # Attach CSV to report and clean up
    if filepath and os.path.exists(filepath):
        with open(filepath, "rb") as f:
            report.csv_file.save(os.path.basename(filepath), File(f), save=True)
        try:
            os.remove(filepath)
        except Exception:
            logger.warning(f"Temporary file {filepath} could not be removed.")

    report.save()
    logger.info(f"Progress report {report.id} generated for project {project_id}.")
    return report.id
