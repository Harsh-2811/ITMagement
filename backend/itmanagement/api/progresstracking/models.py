from django.db import models
from django.conf import settings
from api.projects.models import Project
from api.dailytask.models import DailyTask
from api.projects.models import Milestone
User = settings.AUTH_USER_MODEL
class ProgressUpdate(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="progress_updates")
    task = models.ForeignKey(DailyTask, on_delete=models.SET_NULL, null=True, blank=True, related_name="progress_updates")
    milestone = models.ForeignKey(Milestone, on_delete=models.SET_NULL, null=True, blank=True, related_name="progress_updates")
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2)  # 0 to 100
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.project.name} - {self.progress_percent}%"
class ProgressReport(models.Model):
    """
    Stores generated progress analytics and optional CSV path for download.
    - report_data: JSON with analytics (burndown, metrics, gantt).
    - csv_file: relative path under MEDIA_ROOT (optional) to the generated CSV report.
    """
    project_id = models.PositiveIntegerField()  # store project id 
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    generated_on = models.DateTimeField(auto_now_add=True)
    report_data = models.JSONField(null=True, blank=True)
    csv_file = models.CharField(max_length=1024, blank=True, default="")

    class Meta:
        ordering = ["-generated_on"]

    def __str__(self):
        return f"ProgressReport(project={self.project_id}, on={self.generated_on.isoformat()})"
