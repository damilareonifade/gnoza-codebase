from rest_framework import serializers
from ..models import SmartReminder, ReminderHistory, LearningSchedule


class SmartReminderSerializer(serializers.ModelSerializer):
    is_due = serializers.SerializerMethodField()

    class Meta:
        model = SmartReminder
        fields = [
            "id", "title", "description", "reminder_type",
            "content_link", "first_reminder_at", "next_reminder_at",
            "recurrence_pattern", "custom_schedule", "end_date",
            "status", "delivery_count", "last_delivered_at",
            "metadata", "is_due", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "delivery_count", "last_delivered_at", "created_at", "updated_at"]

    def get_is_due(self, obj) -> bool:
        return obj.is_due()


class ReminderHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderHistory
        fields = [
            "id", "status", "delivered_at", "delivery_method",
            "user_action", "action_timestamp", "content_delivered", "metadata",
        ]
        read_only_fields = ["id", "delivered_at"]


class LearningScheduleSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = LearningSchedule
        fields = [
            "id", "title", "learning_content", "learning_objectives",
            "content_link", "total_sessions", "session_interval_days",
            "sessions", "completed_sessions", "status",
            "progress_percentage", "created_at", "updated_at", "completed_at",
        ]
        read_only_fields = ["id", "completed_sessions", "sessions", "created_at", "updated_at"]

    def get_progress_percentage(self, obj) -> float:
        return obj.progress_percentage()
