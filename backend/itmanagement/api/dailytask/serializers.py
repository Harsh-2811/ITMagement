from rest_framework import serializers
from .models import *
import datetime


class DailyTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyTask
        fields = '__all__'
        read_only_fields = ['assigned_to', 'created_at', 'updated_at']


class TaskDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDependency
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        if data['task'] == data['depends_on']:
            raise serializers.ValidationError("A task cannot depend on itself.")

        visited = set()

        def dfs(task):
            if task.id in visited:
                raise serializers.ValidationError("Circular dependency detected.")
            visited.add(task.id)
            for dep in task.dependencies.all().select_related('depends_on'):
                dfs(dep.depends_on)

    # Only check if both tasks are already saved
        if data['depends_on'].id and data['task'].id:
            dfs(data['depends_on'])

        return data



class TaskTimeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTimeLog
        fields = '__all__'
        read_only_fields = ['user', 'date', 'created_at', 'updated_at']



class StandupReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandupReport
        fields = '__all__'
        read_only_fields = ['user', 'date', 'created_at', 'updated_at']

    def validate(self, data):
        user = self.context['request'].user
        today = datetime.date.today()
        if StandupReport.objects.filter(user=user, date=today).exists():
            raise serializers.ValidationError("You already submitted a standup report for today.")
        return data

