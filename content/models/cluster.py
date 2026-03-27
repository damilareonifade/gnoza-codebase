import re
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from .raw import RawContent


CATEGORY_CHOICES = [
    ("national", "National"),
    ("international", "International"),
    ("sport", "Sport"),
    ("lifestyle", "Lifestyle"),
    ("business", "Business"),
    ("health", "Health"),
    ("fashion", "Fashion"),
    ("technology", "Technology"),
    ("science", "Science"),
    ("art", "Art"),
    ("politics", "Politics"),
]


class ContentCluster(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cluster_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)

    canonical_title = models.CharField(max_length=600)
    canonical_url = models.URLField(max_length=2000)
    merged_snippet = models.TextField()
    image_url = models.URLField(max_length=2000, blank=True, null=True)

    content_type = models.CharField(
        max_length=20,
        choices=[("NEWS", "News"), ("ARTICLE", "Article/Learning"), ("EVENT", "Event")],
        blank=True,
        null=True,
    )
    type_confidence = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    categories = models.JSONField(default=list)
    keywords = models.JSONField(default=list)

    trend_score = models.FloatField(default=0.0, db_index=True)
    importance_score = models.FloatField(default=0.0, db_index=True)
    freshness_score = models.FloatField(default=1.0)
    persistence_score = models.FloatField(default=0.0)
    quality_score = models.FloatField(default=0.5)
    views = models.PositiveIntegerField(default=0, db_index=True)

    short_summary = models.TextField(blank=True)
    medium_summary = models.TextField(blank=True)
    long_summary = models.TextField(blank=True)
    key_points = models.JSONField(default=list)
    synthesis = models.TextField(blank=True)

    source_count = models.PositiveIntegerField(default=1)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)

    full_text_fetched = models.BooleanField(default=False)
    summary_generated = models.BooleanField(default=False)

    location_name = models.CharField(max_length=200, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    event_start_time = models.DateTimeField(blank=True, null=True)
    event_end_time = models.DateTimeField(blank=True, null=True)
    event_venue = models.CharField(max_length=300, blank=True, null=True)
    is_event = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "content_clusters"
        ordering = ["-first_seen_at"]
        indexes = [
            models.Index(fields=["-first_seen_at"]),
            models.Index(fields=["content_type"]),
            models.Index(fields=["-trend_score"]),
            models.Index(fields=["-importance_score"]),
            models.Index(fields=["-last_updated_at"]),
            models.Index(fields=["cluster_hash"]),
            models.Index(fields=["is_event"]),
            models.Index(fields=["location_name"]),
        ]

    def __str__(self):
        prefix = "[EVENT] " if self.is_event else ""
        return f"{prefix}{self.canonical_title[:80]} ({self.source_count} sources)"

    def _clean_text(self, text):
        if not text:
            return text
        text = re.sub(r'\\n+', ' ', text)
        text = re.sub(r'\\r', '', text)
        text = re.sub(r'\\t', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def get_full_text(self):
        """Always returns text — never empty. Priority: long → medium → short → sources → snippet → title."""
        if self.long_summary and len(self.long_summary.strip()) > 100:
            return self._clean_text(self.long_summary.strip())
        if self.medium_summary and len(self.medium_summary.strip()) > 100:
            return self._clean_text(self.medium_summary.strip())
        title_len = len(self.canonical_title or "")
        if self.short_summary and len(self.short_summary.strip()) > title_len + 20:
            return self._clean_text(self.short_summary.strip())
        try:
            all_text = []
            seen = set()
            for source in self.sources.select_related("raw_content").all():
                if source.raw_content:
                    text = None
                    if source.raw_content.full_text and source.raw_content.full_text.strip():
                        text = self._clean_text(source.raw_content.full_text.strip())
                    elif source.raw_content.snippet and source.raw_content.snippet.strip():
                        text = self._clean_text(source.raw_content.snippet.strip())
                    if text:
                        normalized = text.lower().strip()
                        if normalized not in seen:
                            seen.add(normalized)
                            all_text.append(text)
            if all_text:
                combined = "\n\n".join(all_text)
                if len(all_text) == 1 and self.source_count > 1:
                    combined += f"\n\n[Reported by {self.source_count} sources]"
                return combined
        except Exception:
            pass
        if self.merged_snippet and self.merged_snippet.strip():
            return self._clean_text(self.merged_snippet.strip())
        return self.canonical_title or "Content unavailable"

    def get_image_url(self):
        """Always returns an image URL — never empty."""
        if self.image_url:
            return self.image_url
        try:
            for source in self.sources.select_related("raw_content").all():
                if source.raw_content and source.raw_content.image_url:
                    return source.raw_content.image_url
        except Exception:
            pass
        return "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/640px-No_image_available.svg.png"


class ClusterSource(models.Model):
    cluster = models.ForeignKey(
        ContentCluster, on_delete=models.CASCADE, related_name="sources"
    )
    raw_content = models.ForeignKey(
        RawContent, on_delete=models.SET_NULL, null=True, blank=True
    )
    url = models.URLField(max_length=2000)
    source_name = models.CharField(max_length=200)
    credibility_score = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cluster_sources"
        unique_together = ("cluster", "url")
        indexes = [
            models.Index(fields=["cluster", "-added_at"]),
            models.Index(fields=["credibility_score"]),
        ]

    def __str__(self):
        return f"{self.source_name} → {self.cluster.canonical_title[:50]}"

    def get_domain(self):
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            return parsed.netloc.lower().replace("www.", "").split(":")[0]
        except Exception:
            return None

    def save(self, *args, **kwargs):
        if not self.pk:
            domain = self.get_domain()
            if domain:
                for source in ClusterSource.objects.filter(cluster=self.cluster):
                    if source.get_domain() == domain:
                        return  # skip duplicate domain
        super().save(*args, **kwargs)
