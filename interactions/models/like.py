from django.conf import settings
from django.db import models

from content.models import ContentCluster


class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cluster_likes",
    )
    cluster = models.ForeignKey(
        ContentCluster,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_likes"
        unique_together = ("user", "cluster")
        ordering = ["-created_at"]
        verbose_name = "Story Like"
        verbose_name_plural = "Story Likes"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["cluster"]),
        ]

    def __str__(self):
        return f"{self.user} liked {self.cluster.canonical_title[:50]}"
