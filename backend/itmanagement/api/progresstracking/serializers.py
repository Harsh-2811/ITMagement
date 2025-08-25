from rest_framework import serializers
from .models import ProgressReport
from api.dailytask.models import DailyTask
from api.projects.models import Milestone  
from .models import ProgressUpdate
from .models import ProgressUpdate, ProgressReport


class DailyTaskMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyTask
        fields = [
            "id", "title", "description", "assigned_to", "due_date",
            "priority", "category", "status", "sprint", "project_id"
        ]


class MilestoneMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milestone
        fields = ["id", "name", "description", "start_date", "end_date"]


class ProgressUpdateSerializer(serializers.ModelSerializer):
    progress_percent = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)

    class Meta:
        model = ProgressUpdate
        fields = "__all__"
        read_only_fields = ["updated_by", "timestamp"]

    def validate(self, data):
        if not data.get("task") and not data.get("milestone"):
            raise serializers.ValidationError("Either task or milestone must be set.")
        return data

class ProgressReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressReport
        fields = "__all__"
        read_only_fields = ["generated_on"]
