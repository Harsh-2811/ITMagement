from rest_framework import serializers
from .models import DeadlineNotification, EscalationLog

class DeadlineNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeadlineNotification
        fields = "__all__"
        read_only_fields = ["created_at", "sent"]

class EscalationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationLog
        fields = "__all__"
        read_only_fields = ["created_at"]


class CriticalPathSerializer(serializers.Serializer):
    duration_hours = serializers.FloatField()
    path_task_ids = serializers.ListField(child=serializers.IntegerField())


class DeadlineImpactSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    task_id = serializers.IntegerField()
    original_duration_hours = serializers.FloatField()
    new_duration_hours = serializers.FloatField()
    shift_hours = serializers.FloatField()
    shift_days = serializers.FloatField(allow_null=True)
    original_path = serializers.ListField(child=serializers.IntegerField())
    new_path = serializers.ListField(child=serializers.IntegerField())
    error = serializers.CharField(required=False)
