from django.conf import settings
from django.db import models

from content.models import ContentCluster


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    cluster = models.ForeignKey(
        ContentCluster,
        on_delete=models.CASCADE,
        related_name="bookmarked_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bookmarks"
        unique_together = ("user", "cluster")
        ordering = ["-created_at"]
        verbose_name = "Bookmark"
        verbose_name_plural = "Bookmarks"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["cluster"]),
        ]

    def __str__(self):
        return f"{self.user} bookmarked {self.cluster.canonical_title[:50]}"
