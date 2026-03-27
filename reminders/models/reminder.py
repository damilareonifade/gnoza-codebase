import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class SmartReminder(models.Model):
    REMINDER_TYPE_CHOICES = [
        ("learning", "Learning Schedule"),
        ("event", "Event/Deadline"),
        ("personal", "Personal Date (Birthday)"),
        ("content", "Content Deep Dive"),
        ("tracking", "Information Tracking"),
        ("custom", "Custom Reminder"),
    ]

    RECURRENCE_CHOICES = [
        ("once", "One Time"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("biweekly", "Bi-weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
        ("custom", "Custom Pattern"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("archived", "Archived"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="smart_reminders",
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    content_link = models.UUIDField(
        blank=True, null=True, help_text="Optional link to ContentCluster or Event UUID"
    )

    first_reminder_at = models.DateTimeField()
    next_reminder_at = models.DateTimeField(db_index=True)
    recurrence_pattern = models.CharField(
        max_length=20, choices=RECURRENCE_CHOICES, default="once"
    )
    custom_schedule = models.JSONField(default=dict, blank=True)
    end_date = models.DateTimeField(blank=True, null=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active", db_index=True
    )
    delivery_count = models.PositiveIntegerField(default=0)
    last_delivered_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_reminders"
        ordering = ["next_reminder_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "status", "next_reminder_at"]),
            models.Index(fields=["status", "next_reminder_at"]),
            models.Index(fields=["reminder_type"]),
        ]
        verbose_name = "Smart Reminder"
        verbose_name_plural = "Smart Reminders"

    def __str__(self):
        return f"[{self.reminder_type}] {self.title} ({self.status})"

    def is_due(self):
        return (
            self.status == "active"
            and self.next_reminder_at <= timezone.now()
            and (self.end_date is None or self.end_date > timezone.now())
        )
