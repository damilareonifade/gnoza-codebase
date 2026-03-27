from django.db import models
from django.conf import settings


class ContentChat(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="content_chats",
    )
    content_id = models.UUIDField()
    messages = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_chats"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "content_id"]),
        ]

    def __str__(self):
        return f"Chat({self.content_id}) by {self.user}"
