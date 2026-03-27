from django.contrib import admin
from .models import SmartReminder, ReminderHistory, LearningSchedule


@admin.register(SmartReminder)
class SmartReminderAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "reminder_type", "status", "next_reminder_at", "delivery_count")
    list_filter = ("status", "reminder_type", "recurrence_pattern")
    search_fields = ("user__email", "title")
    raw_id_fields = ("user",)
    ordering = ("next_reminder_at",)


@admin.register(ReminderHistory)
class ReminderHistoryAdmin(admin.ModelAdmin):
    list_display = ("reminder", "status", "delivery_method", "user_action", "delivered_at")
    list_filter = ("status", "user_action", "delivery_method")
    raw_id_fields = ("reminder",)


@admin.register(LearningSchedule)
class LearningScheduleAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "completed_sessions", "total_sessions", "created_at")
    list_filter = ("status",)
    search_fields = ("user__email", "title")
    raw_id_fields = ("user",)
