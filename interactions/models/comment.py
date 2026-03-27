from django.conf import settings
from django.db import models

from content.models import ContentCluster


class Comment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    cluster = models.ForeignKey(
        ContentCluster,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    text = models.TextField(max_length=2000)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comments"
        ordering = ["-created_at"]
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        indexes = [
            models.Index(fields=["cluster", "-created_at"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        preview = self.text[:50] + ("..." if len(self.text) > 50 else "")
        return f"Comment by {self.user}: {preview}"

    @property
    def like_count(self):
        if hasattr(self, "comment_likes_count"):
            return self.comment_likes_count
        return self.comment_likes.count()

    def is_liked_by(self, user):
        if not user.is_authenticated:
            return False
        return self.comment_likes.filter(user=user).exists()


class CommentLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_likes",
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="comment_likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comment_likes"
        unique_together = ("user", "comment")
        ordering = ["-created_at"]
        verbose_name = "Comment Like"
        verbose_name_plural = "Comment Likes"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["comment"]),
        ]

    def __str__(self):
        return f"{self.user} liked comment {self.comment.id}"
