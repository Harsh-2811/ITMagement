from django.db import models
# from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from api.projects.models import Project
from django.contrib.auth import get_user_model

User = get_user_model()

class Sprint(models.Model):
    name = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sprints')
    start_date = models.DateField()
    end_date = models.DateField()
    goal = models.TextField()
    team_members = models.ManyToManyField(User, related_name='sprints')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    def duration(self):
        return (self.end_date - self.start_date).days

    def is_active(self):
        from datetime import date
        today = date.today()
        return self.start_date <= today <= self.end_date

    def get_duration_display(self):
        return f"{self.duration()} days"


class Story(models.Model):

    class SizingChoices(models.TextChoices):
        XS = 'XS', _('Extra Small')
        S = 'S', _('Small')
        M = 'M', _('Medium')
        L = 'L', _('Large')
        XL = 'XL', _('Extra Large')

    class StatusChoices(models.TextChoices):
        TODO = 'To Do', _('To Do')
        IN_PROGRESS = 'In Progress', _('In Progress')
        DONE = 'Done', _('Done')

    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name='stories')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='stories')
    title = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    story_points = models.PositiveIntegerField(default=0)
    t_shirt_size = models.CharField(
        max_length=2,
        choices=SizingChoices.choices,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.TODO
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Retrospective(models.Model):
    sprint = models.OneToOneField(Sprint, on_delete=models.CASCADE, related_name='retrospective')
    what_went_well = models.TextField()
    what_didnt_go_well = models.TextField()
    improvements = models.TextField()
    action_items = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Retrospective for {self.sprint.name}"
