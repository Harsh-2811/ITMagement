from django.contrib import admin
from .models import Client, Project, ProjectScope, Budget, TeamMember, User, Milestone
# Register your models here.
admin.site.register(Client)
admin.site.register(Project)
admin.site.register(ProjectScope)
admin.site.register(Budget)
admin.site.register(TeamMember)
admin.site.register(User)
admin.site.register(Milestone)