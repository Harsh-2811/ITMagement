from django.db import models
from django.conf import settings 
from ..sprints.models import Sprint
from ..projects.models import Project



class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DailyTask(TimeStampedModel):
    class Priority(models.TextChoices):
        HIGH = 'High', 'High'
        MEDIUM = 'Medium', 'Medium'
        LOW = 'Low', 'Low'

    class Category(models.TextChoices):
        DEVELOPMENT = 'Development', 'Development'
        DESIGN = 'Design', 'Design'
        TESTING = 'Testing', 'Testing'
        OTHER = 'Other', 'Other'

    class Status(models.TextChoices):
        TODO = 'To Do', 'To Do'
        IN_PROGRESS = 'In Progress', 'In Progress'
        DONE = 'Done', 'Done'
        BLOCKED = 'Blocked', 'Blocked'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_tasks')  
    due_date = models.DateField()
    priority = models.CharField(max_length=10, choices=Priority.choices)
    category = models.CharField(max_length=20, choices=Category.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_tasks')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='daily_tasks')

    def __str__(self):
        return self.title or f"Task #{self.id}"


class TaskDependency(TimeStampedModel):
    task = models.ForeignKey(DailyTask, on_delete=models.CASCADE, related_name='dependencies')
    depends_on = models.ForeignKey(DailyTask, on_delete=models.CASCADE, related_name='blocking_tasks')

    def __str__(self):
        return f"{self.task.title} depends on {self.depends_on.title}"


class TaskTimeLog(TimeStampedModel):
    task = models.ForeignKey(DailyTask, on_delete=models.CASCADE, related_name='time_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) 
    date = models.DateField(auto_now_add=True)
    hours_spent = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.task.title} - {self.hours_spent} hrs"


class StandupReport(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) 
    date = models.DateField(auto_now_add=True)
    yesterday = models.TextField()
    today = models.TextField()
    blockers = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name='unique_standup_per_day')
        ]

    def __str__(self):
        return f"{self.user.username} - Standup {self.date}"
