import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class LearningSchedule(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="learning_schedules",
    )
    title = models.CharField(max_length=300)
    learning_content = models.TextField()
    learning_objectives = models.JSONField(default=list, blank=True)
    content_link = models.UUIDField(blank=True, null=True)

    total_sessions = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    session_interval_days = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    sessions = models.JSONField(default=list)
    completed_sessions = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active", db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "learning_schedules"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]
        verbose_name = "Learning Schedule"
        verbose_name_plural = "Learning Schedules"

    def __str__(self):
        return f"{self.title} ({self.completed_sessions}/{self.total_sessions})"

    def progress_percentage(self):
        if self.total_sessions == 0:
            return 0
        return int((self.completed_sessions / self.total_sessions) * 100)

    def generate_sessions(self):
        sessions = []
        start = timezone.now()
        for i in range(1, self.total_sessions + 1):
            scheduled = start + timedelta(days=(i - 1) * self.session_interval_days)
            sessions.append({
                "session_number": i,
                "scheduled_for": scheduled.isoformat(),
                "completed": False,
                "notes": "",
            })
        self.sessions = sessions
        return sessions
