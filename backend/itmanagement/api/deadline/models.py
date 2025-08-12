from django.db import models
from django.conf import settings
from dailytask.models import DailyTask
from projects.models import Project, Milestone
from sprints.models import Sprint

User = settings.AUTH_USER_MODEL

class DeadlineNotification(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="deadline_notifications")
    task = models.ForeignKey(DailyTask, null=True, blank=True, on_delete=models.CASCADE, related_name="deadline_notifications")
    milestone = models.ForeignKey(Milestone, null=True, blank=True, on_delete=models.CASCADE, related_name="deadline_notifications")
    sprint = models.ForeignKey(Sprint, null=True, blank=True, on_delete=models.CASCADE, related_name="deadline_notifications")
    notify_at = models.DateTimeField()
    sent = models.BooleanField(default=False)
    escalation = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["notify_at", "sent"]),
            models.Index(fields=["project"]),
        ]

    def __str__(self):
        return f"DeadlineNotification(project={self.project_id}, notify_at={self.notify_at}, sent={self.sent})"


class EscalationLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="escalation_logs")
    task = models.ForeignKey(DailyTask, null=True, blank=True, on_delete=models.CASCADE, related_name="escalation_logs")
    milestone = models.ForeignKey(Milestone, null=True, blank=True, on_delete=models.CASCADE, related_name="escalation_logs")
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True)
    notified_users = models.JSONField(null=True, blank=True)  # List of user IDs or emails

    def __str__(self):
        return f"EscalationLog(project={self.project_id}, at={self.created_at.isoformat()})"
