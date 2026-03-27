from django.conf import settings
from django.db import models

from .topic import Topic


class UserTopic(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_topics",
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="user_topics",
    )
    is_saved = models.BooleanField(default=True)
    saved_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_topics"
        unique_together = ["user", "topic"]
        ordering = ["-saved_at"]
        verbose_name = "User Topic"
        verbose_name_plural = "User Topics"

    def __str__(self):
        return f"{self.user} — {self.topic.name}"
