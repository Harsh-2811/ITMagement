from django.contrib import admin
from .models import DailyTask, TaskDependency, TaskTimeLog, StandupReport

admin.site.register(DailyTask)
admin.site.register(TaskDependency)
admin.site.register(TaskTimeLog)
admin.site.register(StandupReport)
