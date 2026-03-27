import uuid
from django.db import models


class RawContent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    source_type = models.CharField(max_length=50)
    source_name = models.CharField(max_length=200, blank=True)
    external_id = models.CharField(max_length=300, blank=True)

    url = models.URLField(max_length=2000, unique=True)
    title = models.CharField(max_length=600)
    snippet = models.TextField(blank=True)
    full_text = models.TextField(blank=True, null=True, default="")
    image_url = models.URLField(max_length=2000, blank=True, null=True)

    published_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now_add=True)

    raw_data = models.JSONField(default=dict)
    processed = models.BooleanField(default=False, db_index=True)

    cluster_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)

    class Meta:
        db_table = "raw_content"
        ordering = ["-fetched_at"]
        indexes = [
            models.Index(fields=["processed", "-fetched_at"]),
            models.Index(fields=["source_type"]),
            models.Index(fields=["published_at"]),
            models.Index(fields=["-published_at"]),
            models.Index(fields=["cluster_hash"]),
        ]

    def __str__(self):
        return f"[{self.source_type}:{self.source_name}] {self.title[:70]}"
