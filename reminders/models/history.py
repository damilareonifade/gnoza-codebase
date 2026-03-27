import uuid
from django.db import models

from .reminder import SmartReminder


class ReminderHistory(models.Model):
    DELIVERY_STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("skipped", "Skipped"),
    ]

    USER_ACTION_CHOICES = [
        ("none", "No Action"),
        ("clicked", "Clicked"),
        ("dismissed", "Dismissed"),
        ("postponed", "Postponed"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reminder = models.ForeignKey(
        SmartReminder, on_delete=models.CASCADE, related_name="delivery_history"
    )
    status = models.CharField(
        max_length=20, choices=DELIVERY_STATUS_CHOICES, default="sent"
    )
    delivered_at = models.DateTimeField(auto_now_add=True)
    delivery_method = models.CharField(max_length=50, default="push")
    user_action = models.CharField(
        max_length=20, choices=USER_ACTION_CHOICES, default="none"
    )
    action_timestamp = models.DateTimeField(blank=True, null=True)
    content_delivered = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "reminder_history"
        ordering = ["-delivered_at"]
        indexes = [
            models.Index(fields=["reminder", "-delivered_at"]),
            models.Index(fields=["status"]),
        ]
        verbose_name = "Reminder History"
        verbose_name_plural = "Reminder Histories"

    def __str__(self):
        return f"{self.reminder.title} — {self.status} ({self.delivered_at})"
