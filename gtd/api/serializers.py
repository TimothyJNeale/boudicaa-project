# SDS 7.3 — API serializers
from rest_framework import serializers

from gtd.models import (
    Action,
    Area,
    Context,
    Domain,
    InboxItem,
    Priority,
    Project,
    Status,
    UserProfile,
    WorkSession,
)


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ['id', 'name', 'color', 'created_at']
        read_only_fields = ['created_at']


class AreaSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = Area
        fields = ['id', 'name', 'domain', 'domain_name', 'created_at']
        read_only_fields = ['created_at']


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ['id', 'name', 'color', 'activity_level']


class PrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Priority
        fields = ['id', 'name', 'rank']


class ContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = Context
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['created_at']


class InboxItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InboxItem
        fields = ['id', 'item', 'area', 'processed_at', 'processing_note', 'created_at']
        read_only_fields = ['processed_at', 'processing_note', 'created_at']


class ProjectSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source='area.name', read_only=True)
    status_name = serializers.CharField(source='status.name', read_only=True)
    incomplete_action_count = serializers.IntegerField(read_only=True)
    completed_action_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'slug', 'description', 'notes',
            'area', 'area_name', 'status', 'status_name',
            'parent_project', 'created_at', 'ended_at', 'is_protected',
            'incomplete_action_count', 'completed_action_count',
        ]
        read_only_fields = ['slug', 'created_at', 'ended_at', 'is_protected']


class ActionSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    area_name = serializers.CharField(source='area.name', read_only=True)
    priority_name = serializers.CharField(source='priority.name', read_only=True)
    context_name = serializers.CharField(source='context.name', read_only=True, default=None)
    is_overdue = serializers.BooleanField(read_only=True)
    is_recurring = serializers.BooleanField(read_only=True)
    total_time_worked = serializers.DurationField(read_only=True)

    class Meta:
        model = Action
        fields = [
            'id', 'name', 'notes', 'display_order',
            'scheduled_start', 'scheduled_end', 'started_at', 'ended_at',
            'waiting_on', 'time_budgeted', 'is_skipped',
            'project', 'project_name', 'area', 'area_name',
            'priority', 'priority_name', 'context', 'context_name',
            'recurrence_rule', 'recurrence_end',
            'is_overdue', 'is_recurring', 'total_time_worked',
            'created_at',
        ]
        read_only_fields = ['started_at', 'ended_at', 'created_at']


class WorkSessionSerializer(serializers.ModelSerializer):
    action_name = serializers.CharField(source='action.name', read_only=True)
    project_name = serializers.CharField(source='action.project.name', read_only=True)
    elapsed_time_formatted = serializers.CharField(read_only=True)
    elapsed_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkSession
        fields = [
            'id', 'started_at', 'finished_at', 'action', 'action_name',
            'project_name', 'notes', 'elapsed_time_formatted', 'elapsed_minutes',
            'created_at',
        ]
        read_only_fields = ['created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    days_since_review = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserProfile
        fields = ['preferred_project_view', 'last_review_date', 'days_since_review']
