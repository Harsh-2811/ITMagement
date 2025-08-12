from rest_framework import serializers
from .models import Client, Project, ProjectScope, Budget , TeamMember, User , Milestone

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

    def validate(self, data):
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError("End date must be after start date.")
        return data


class ProjectDetailSerializer(serializers.ModelSerializer):
    client = ClientSerializer()

    class Meta:
        model = Project
        fields = '__all__'


class ProjectScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectScope
        fields = '__all__'

    def validate_project(self, value):
        if ProjectScope.objects.filter(project=value).exists() and not self.instance:
            raise serializers.ValidationError("Scope for this project already exists.")
        return value


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = '__all__'

    def validate_project(self, value):
        if Budget.objects.filter(project=value).exists() and not self.instance:
            raise serializers.ValidationError("Budget for this project already exists.")
        return value



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class TeamMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    project = ProjectSerializer()

    class Meta:
        model = TeamMember
        fields = '__all__'


class TeamMemberCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = ['user', 'project', 'role']


class MilestoneSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Milestone
        fields = [
            'id', 'project', 'name', 'description',
            'start_date', 'end_date',
            'is_completed', 'completed_at', 'is_overdue'
        ]
        read_only_fields = ['completed_at', 'is_overdue']
