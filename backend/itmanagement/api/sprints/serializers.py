from rest_framework import serializers
from .models import Sprint, Story, Retrospective
from django.contrib.auth import get_user_model

User = get_user_model()

class RetrospectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Retrospective
        fields = '__all__'


class SprintSerializer(serializers.ModelSerializer):
    team_members = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True)
    retrospective = RetrospectiveSerializer(read_only=True)
    duration_display = serializers.SerializerMethodField()

    class Meta:
        model = Sprint
        fields = '__all__'  

    def get_duration_display(self, obj):
        return obj.get_duration_display()
    
    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("End date must be after start date.")
    
        project = data['project']
        start_date = data['start_date']
        end_date = data['end_date']

        overlapping_sprints = Sprint.objects.filter(
            project=project,
            end_date__gte=start_date,
            start_date__lte=end_date
        )
    
        if self.instance:
            overlapping_sprints = overlapping_sprints.exclude(pk=self.instance.pk)
    
        if overlapping_sprints.exists():
            raise serializers.ValidationError("This sprint overlaps with another sprint in the same project.")
    
        return data


class StorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = '__all__'
