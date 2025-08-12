from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.conf import settings 
from django.utils import timezone

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Client(TimeStampedModel):
    name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    billing_preferences = models.TextField(blank=True)

    def __str__(self):
        return self.name


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
    project_id = models.CharField(max_length=100, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    department = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.project_id})"


class ProjectScope(TimeStampedModel):
    project = models.OneToOneField(Project, on_delete=models.CASCADE)
    objectives = models.TextField()
    deliverables = models.TextField()
    functional_requirements = models.TextField()
    non_functional_requirements = models.TextField()
    in_scope = models.TextField()
    out_of_scope = models.TextField()
    dependencies = models.TextField()
    assumptions = models.TextField()

    def __str__(self):
        return f"Scope for {self.project.name}"


class Budget(TimeStampedModel):
    project = models.OneToOneField(Project, on_delete=models.CASCADE)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    def __str__(self):
        return f"Budget for {self.project.name}"


    
class TeamMember(TimeStampedModel):

    class Role(models.TextChoices):
        PROJECT_MANAGER = 'Project Manager', _('Project Manager')
        DEVELOPER = 'Developer', _('Developer')
        DESIGNER = 'Designer', _('Designer')
        TESTER = 'Tester', _('Tester')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # ✅ Fixed
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='team_members')
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.DEVELOPER
    )

    def __str__(self):
        return f"{self.user.username} - {self.role} in {self.project.name}"



class Milestone(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()

    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

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

