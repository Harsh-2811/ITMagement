from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
from django.contrib.auth import get_user_model

User = get_user_model() 

# Base Model

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True



# Client Model
class Client(TimeStampedModel):
    name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    billing_preferences = models.TextField(blank=True)

    def __str__(self):
        return self.name



# Project Model
class Project(TimeStampedModel):

    class Status(models.TextChoices):
        PLANNING = 'Planning', _('Planning')
        ACTIVE = 'Active', _('Active')
        COMPLETED = 'Completed', _('Completed')

    class Priority(models.TextChoices):
        HIGH = 'High', _('High')
        MEDIUM = 'Medium', _('Medium')
        LOW = 'Low', _('Low')

    name = models.CharField(max_length=255)
    project_id = models.CharField(max_length=100, unique=True, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    department = models.CharField(max_length=100)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.project_id:
            self.project_id = f"PRJ-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.project_id})"


# Project Scope
class ProjectScope(TimeStampedModel):
    project = models.OneToOneField(Project, on_delete=models.CASCADE)
    objectives = models.TextField(blank=True)
    deliverables = models.TextField(blank=True)
    functional_requirements = models.TextField(blank=True)
    non_functional_requirements = models.TextField(blank=True)
    in_scope = models.TextField(blank=True)
    out_of_scope = models.TextField(blank=True)
    dependencies = models.TextField(blank=True)
    assumptions = models.TextField(blank=True)

    def __str__(self):
        return f"Scope for {self.project.name}"



# Budget
class Budget(TimeStampedModel):
    project = models.OneToOneField(Project, on_delete=models.CASCADE)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    @property
    def variance(self):
        return self.actual_cost - self.estimated_cost

    def __str__(self):
        return f"Budget for {self.project.name}"


# -----------------------
# Team Member
# -----------------------
class TeamMember(TimeStampedModel):

    class Role(models.TextChoices):
        PROJECT_MANAGER = 'Project Manager', _('Project Manager')
        DEVELOPER = 'Developer', _('Developer')
        DESIGNER = 'Designer', _('Designer')
        TESTER = 'Tester', _('Tester')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='team_members')
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.DEVELOPER)

    class Meta:
        unique_together = ('user', 'project')

    def __str__(self):
        return f"{self.user.username} - {self.role} in {self.project.name}"


# -----------------------
# Milestone
# -----------------------
class Milestone(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['end_date']

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    @property
    def is_overdue(self):
        return not self.is_completed and timezone.now().date() > self.end_date

    def mark_complete(self):
        if not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            self.save()


# -----------------------
# Deadline Notification
# -----------------------
class DeadlineNotification(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="deadline_notifications")
    task = models.ForeignKey("dailytask.DailyTask", null=True, blank=True, on_delete=models.CASCADE, related_name="deadline_notifications")
    milestone = models.ForeignKey("Milestone", null=True, blank=True, on_delete=models.CASCADE, related_name="deadline_notifications")
    sprint = models.ForeignKey("sprints.Sprint", null=True, blank=True, on_delete=models.CASCADE, related_name="deadline_notifications")
    notify_at = models.DateTimeField()
    sent = models.BooleanField(default=False)
    escalation = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["notify_at", "sent"]),
            models.Index(fields=["project"]),
        ]

    def clean(self):
        super().clean()
        linked_items = [self.task, self.milestone, self.sprint]
        if sum(bool(x) for x in linked_items) != 1:
            raise ValidationError("Exactly one of task, milestone, or sprint must be set.")

    def __str__(self):
        return f"DeadlineNotification({self.project_id}, notify_at={self.notify_at}, sent={self.sent})"


# -----------------------
# Escalation Log
# -----------------------
class EscalationLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="escalation_logs")
    task = models.ForeignKey("dailytask.DailyTask", null=True, blank=True, on_delete=models.CASCADE, related_name="escalation_logs")
    milestone = models.ForeignKey("Milestone", null=True, blank=True, on_delete=models.CASCADE, related_name="escalation_logs")
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True)
    notified_users = models.JSONField(null=True, blank=True)  # List of user IDs or emails

    def __str__(self):
        return f"EscalationLog(project={self.project_id}, at={self.created_at.isoformat()})"



# from django.db import models
# from django.conf import settings
# from django.utils.translation import gettext_lazy as _
# from django.utils import timezone
# from django.core.exceptions import ValidationError
# import uuid

# from api.dailytask.models import DailyTask
# from api.sprints.models import Sprint



# # Base Model
# class TimeStampedModel(models.Model):
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         abstract = True


# # Client Model
# class Client(TimeStampedModel):
#     name = models.CharField(max_length=255)
#     organization = models.CharField(max_length=255)
#     email = models.EmailField()
#     phone = models.CharField(max_length=20)
#     billing_preferences = models.TextField(blank=True)

#     def __str__(self):
#         return self.name



# # Project Model
# class Project(TimeStampedModel):

#     class Status(models.TextChoices):
#         PLANNING = 'Planning', _('Planning')
#         ACTIVE = 'Active', _('Active')
#         COMPLETED = 'Completed', _('Completed')

#     class Priority(models.TextChoices):
#         HIGH = 'High', _('High')
#         MEDIUM = 'Medium', _('Medium')
#         LOW = 'Low', _('Low')

#     name = models.CharField(max_length=255)
#     project_id = models.CharField(max_length=100, unique=True, editable=False)
#     client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
#     start_date = models.DateField()
#     end_date = models.DateField()
#     status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)
#     priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
#     department = models.CharField(max_length=100)

#     class Meta:
#         ordering = ['-created_at']

#     def save(self, *args, **kwargs):
#         if not self.project_id:
#             self.project_id = f"PRJ-{uuid.uuid4().hex[:8].upper()}"
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.name} ({self.project_id})"



# # Project Scope
# class ProjectScope(TimeStampedModel):
#     project = models.OneToOneField(Project, on_delete=models.CASCADE)
#     objectives = models.TextField(blank=True)
#     deliverables = models.TextField(blank=True)
#     functional_requirements = models.TextField(blank=True)
#     non_functional_requirements = models.TextField(blank=True)
#     in_scope = models.TextField(blank=True)
#     out_of_scope = models.TextField(blank=True)
#     dependencies = models.TextField(blank=True)
#     assumptions = models.TextField(blank=True)

#     def __str__(self):
#         return f"Scope for {self.project.name}"


# # Budget
# class Budget(TimeStampedModel):
#     project = models.OneToOneField(Project, on_delete=models.CASCADE)
#     estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
#     actual_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

#     @property
#     def variance(self):
#         return self.actual_cost - self.estimated_cost

#     def __str__(self):
#         return f"Budget for {self.project.name}"



# # Team Member
# class TeamMember(TimeStampedModel):

#     class Role(models.TextChoices):
#         PROJECT_MANAGER = 'Project Manager', _('Project Manager')
#         DEVELOPER = 'Developer', _('Developer')
#         DESIGNER = 'Designer', _('Designer')
#         TESTER = 'Tester', _('Tester')

#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='team_members')
#     role = models.CharField(max_length=50, choices=Role.choices, default=Role.DEVELOPER)

#     class Meta:
#         unique_together = ('user', 'project')

#     def __str__(self):
#         return f"{self.user.username} - {self.role} in {self.project.name}"



# # Milestone
# class Milestone(TimeStampedModel):
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
#     name = models.CharField(max_length=255)
#     description = models.TextField(blank=True)
#     start_date = models.DateField()
#     end_date = models.DateField()
#     is_completed = models.BooleanField(default=False)
#     completed_at = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         ordering = ['end_date']

#     def __str__(self):
#         return f"{self.name} ({self.project.name})"

#     @property
#     def is_overdue(self):
#         return not self.is_completed and timezone.now().date() > self.end_date

#     def mark_complete(self):
#         if not self.is_completed:
#             self.is_completed = True
#             self.completed_at = timezone.now()
#             self.save()



# # Deadline Notification
# class DeadlineNotification(models.Model):
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="deadline_notifications")
#     task = models.ForeignKey(DailyTask, null=True, blank=True, on_delete=models.CASCADE, related_name="deadline_notifications")
#     milestone = models.ForeignKey(Milestone, null=True, blank=True, on_delete=models.CASCADE, related_name="deadline_notifications")
#     sprint = models.ForeignKey(Sprint, null=True, blank=True, on_delete=models.CASCADE, related_name="deadline_notifications")
#     notify_at = models.DateTimeField()
#     sent = models.BooleanField(default=False)
#     escalation = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         indexes = [
#             models.Index(fields=["notify_at", "sent"]),
#             models.Index(fields=["project"]),
#         ]

#     def clean(self):
#         super().clean()
#         linked_items = [self.task, self.milestone, self.sprint]
#         if sum(bool(x) for x in linked_items) != 1:
#             raise ValidationError("Exactly one of task, milestone, or sprint must be set.")

#     def __str__(self):
#         return f"DeadlineNotification({self.project_id}, notify_at={self.notify_at}, sent={self.sent})"


# # Escalation Log
# class EscalationLog(models.Model):
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="escalation_logs")
#     task = models.ForeignKey(DailyTask, null=True, blank=True, on_delete=models.CASCADE, related_name="escalation_logs")
#     milestone = models.ForeignKey(Milestone, null=True, blank=True, on_delete=models.CASCADE, related_name="escalation_logs")
#     created_at = models.DateTimeField(auto_now_add=True)
#     message = models.TextField(blank=True)
#     notified_users = models.JSONField(null=True, blank=True)  # List of user IDs or emails

#     def __str__(self):
#         return f"EscalationLog(project={self.project_id}, at={self.created_at.isoformat()})"
