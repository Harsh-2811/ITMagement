from django.contrib import admin
from .models import Sprint, Story, Retrospective
# Register your models here.
admin.site.register(Sprint)
admin.site.register(Story)
admin.site.register(Retrospective)
