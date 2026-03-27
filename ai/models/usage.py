import uuid
from django.conf import settings
from django.db import models

from gnoza.models import TimestampedModel


class GeminiUsage(TimestampedModel):
    MODEL_CHOICES = [
        ("flash", "Gemini Flash"),
        ("pro", "Gemini Pro"),
    ]

    TASK_CHOICES = [
        ("summary", "Content Summary"),
        ("synthesis", "Cluster Synthesis"),
        ("chat", "Content Chat"),
        ("deep_dive", "Deep Dive Analysis"),
        ("ask_gnoza", "Ask Gnoza"),
        ("reminder_parse", "Reminder NLP Parse"),
        ("learning_schedule", "Learning Schedule"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gemini_usage",
    )
    model = models.CharField(max_length=20, choices=MODEL_CHOICES)
    task = models.CharField(max_length=30, choices=TASK_CHOICES, default="other")
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "gemini_usage"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["task"]),
        ]
        verbose_name = "Gemini Usage"
        verbose_name_plural = "Gemini Usage"

    def __str__(self):
        return f"{self.task} ({self.model}) — {self.total_tokens} tokens"
