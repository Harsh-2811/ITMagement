import os
import csv
from django.conf import settings
from background_task import background
from django.utils import timezone
from .models import ProgressReport
from .utils import burndown_series, gantt_payload, performance_metrics, ensure_report_dir
from django.contrib.auth import get_user_model
from api.dailytask.models import DailyTask

User = get_user_model()

def convert_uuids(obj):
    if isinstance(obj, dict):
        return {k: convert_uuids(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_uuids(v) for v in obj]
    elif hasattr(obj, "hex"):  # UUID object
        return str(obj)
    else:
        return obj
    
# @background(schedule=5)
# def generate_progress_report(project_id, user_id=None):
#     """
#     Background job to generate JSON analytics and CSV file.
#     Saves ProgressReport (report_data) and csv_file relative to MEDIA_ROOT.
#     """
#     # Ensure project_id is string
#     project_id = str(project_id)

#     # compute analytics
#     data = {
#         "burndown": burndown_series(project_id, days=30),
#         "gantt": gantt_payload(project_id),
#         "metrics": performance_metrics(project_id)
#     }

#     csv_relpath = ""
#     try:
#         out_dir = ensure_report_dir()
#         ts = timezone.now().strftime("%Y%m%d_%H%M%S")
#         filename = f"progress_report_project_{project_id}_{ts}.csv"
#         filepath = os.path.join(out_dir, filename)

#         # write CSV with tasks summary
#         tasks = DailyTask.objects.filter(project__project_id=project_id).select_related("assigned_to", "sprint")
#         with open(filepath, "w", newline="", encoding="utf-8") as fh:
#             writer = csv.writer(fh)
#             writer.writerow([
#                 "Task ID", "Title", "Assignee", "Status", "Priority", "Category",
#                 "Estimated Hours", "Logged Hours", "Remaining Hours", "Start Date", "Due Date"
#             ])
#             for t in tasks:
#                 est = getattr(t, "estimated_hours", "")
#                 try:
#                     from .utils import _get_task_logged_hours
#                     logged = _get_task_logged_hours(t)
#                 except Exception:
#                     logged = getattr(t, "logged_hours", "")
#                 try:
#                     remaining = (float(est) - float(logged)) if est != "" and logged != "" else ""
#                 except Exception:
#                     remaining = ""
#                 writer.writerow([
#                     t.id,
#                     getattr(t, "title", getattr(t, "name", "")),
#                     getattr(getattr(t, "assigned_to", None), "username", ""),
#                     getattr(t, "status", ""),
#                     getattr(t, "priority", ""),
#                     getattr(t, "category", ""),
#                     est,
#                     logged,
#                     remaining,
#                     getattr(t, "start_date", "") and getattr(t, "start_date").isoformat(),
#                     getattr(t, "due_date", "") and getattr(t, "due_date").isoformat(),
#                 ])
#         csv_relpath = os.path.join("progress_reports", filename)
#     except Exception:
#         csv_relpath = ""

#     # get user object
#     user = None
#     if user_id:
#         try:
#             user = User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             user = None

#     # store ProgressReport
#     report = ProgressReport.objects.create(
#         project_id=project_id,
#         generated_by=user,
#         report_data=data,
#         csv_file=csv_relpath
#     )

#     return report.id
# background_tasks.py
import os
import csv
from django.conf import settings
from background_task import background
from django.utils import timezone
from .models import ProgressReport
from .utils import burndown_series, gantt_payload, performance_metrics, ensure_report_dir
from django.contrib.auth import get_user_model
from api.dailytask.models import DailyTask
from api.projects.models import Project

User = get_user_model()
# ensure user variable always exists


@background(schedule=5)
def generate_progress_report(project_id, user_id=None):
    def convert_uuids(obj):
        if isinstance(obj, dict):
            return {k: convert_uuids(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_uuids(v) for v in obj]
        elif hasattr(obj, "hex"):  # UUID object
            return str(obj)
        else:
            return obj

# In generate_progress_report, before saving:
    data = {
        "burndown": burndown_series(project_id, days=30),
        "gantt": gantt_payload(project_id),
        "metrics": performance_metrics(project_id)
    }

# convert UUIDs in analytics to strings
    data = convert_uuids(data)
    user = None
    if user_id is not None:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            user = None
# then create ProgressReport
    report = ProgressReport.objects.create(
        project_id=project_id,
        generated_by=user,
        report_data=data,
        csv_file=csv_relpath
    )

    """
    Background job to generate JSON analytics and CSV file.
    Saves ProgressReport (report_data) and csv_file relative to MEDIA_ROOT.
    """
    # Fetch project object
    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        return None  # project deleted, stop task

    project_code = project.project_id  # string for filenames/logging

    # compute analytics
    data = {
        "burndown": burndown_series(project_id, days=30),
        "gantt": gantt_payload(project_id),
        "metrics": performance_metrics(project_id)
    }

    csv_relpath = ""
    try:
        out_dir = ensure_report_dir()
        ts = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"progress_report_{project_code}_{ts}.csv"
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
        csv_relpath = os.path.join("progress_reports", filename)
    except Exception:
        csv_relpath = ""

    # get user object
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            user = None

    # store ProgressReport
    report = ProgressReport.objects.create(
        project_id=project_id,  # integer PK
        generated_by=user,
        report_data=data,
        csv_file=csv_relpath
    )

    return report.id
