import os
import csv
from django.conf import settings
from background_tasks import background
from django.utils import timezone
from .models import ProgressReport
from .utils import burndown_series, gantt_payload, performance_metrics, ensure_report_dir
from django.contrib.auth import get_user_model
from dailytask.models import DailyTask


User = get_user_model()

@background(schedule=5)
def generate_progress_report(project_id, user_id=None):
    """
    Background job to generate JSON analytics and CSV file.
    Saves ProgressReport (report_data) and csv_file relative to MEDIA_ROOT.
    """
    # compute analytics
    data = {
        "burndown": burndown_series(project_id, days=30),
        "gantt": gantt_payload(project_id),
        "metrics": performance_metrics(project_id)
    }

    csv_relpath = ""
    # create CSV file
    try:
        out_dir = ensure_report_dir()
        ts = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"progress_report_project_{project_id}_{ts}.csv"
        filepath = os.path.join(out_dir, filename)
        # write CSV with tasks summary
        tasks = DailyTask.objects.filter(project_id=project_id).select_related("assigned_to", "sprint")
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                "Task ID", "Title", "Assignee", "Status", "Priority", "Category",
                "Estimated Hours", "Logged Hours", "Remaining Hours", "Start Date", "Due Date"
            ])
            for t in tasks:
                est = getattr(t, "estimated_hours", "")
                # compute logged hours using TaskTimeLog if exists via utils
                try:
                    from .utils import _get_task_logged_hours
                    logged = _get_task_logged_hours(t)
                except Exception:
                    logged = getattr(t, "logged_hours", "")
                try:
                    remaining = (float(est) - float(logged)) if est != "" and logged != "" else ""
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
                    getattr(t, "start_date", "") and getattr(t, "start_date").isoformat(),
                    getattr(t, "due_date", "") and getattr(t, "due_date").isoformat(),
                ])
        # store relative path (relative to MEDIA_ROOT)
        csv_relpath = os.path.join("progress_reports", filename)
    except Exception as e:
        # CSV generation failed; continue to save JSON report
        csv_relpath = ""
    # store ProgressReport
    user = None
    try:
        if user_id:
            user = User.objects.get(id=user_id)
    except Exception:
        user = None
    report = ProgressReport.objects.create(
        project_id=project_id,
        generated_by=user,
        report_data=data,
        csv_file=csv_relpath
    )
    return report.id
