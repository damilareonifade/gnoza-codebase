import uuid
from django.db import models
from django.conf import settings


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    canonical_title = models.CharField(max_length=600)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=2000, blank=True, null=True)

    short_summary = models.TextField(blank=True)
    medium_summary = models.TextField(blank=True)
    long_summary = models.TextField(blank=True)
    summary_generated = models.BooleanField(default=False)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)

    venue_name = models.CharField(max_length=300, blank=True)
    location_name = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    categories = models.JSONField(default=list)
    keywords = models.JSONField(default=list)

    source_count = models.PositiveIntegerField(default=1)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "events"
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["start_time"]),
            models.Index(fields=["-start_time"]),
            models.Index(fields=["location_name"]),
        ]

    def __str__(self):
        return f"[EVENT] {self.canonical_title[:80]} @ {self.location_name}"

    @property
    def title(self):
        return self.canonical_title

    @property
    def attendee_count(self):
        return self.attendees.count()

    @property
    def event_url(self):
        first = self.sources.first()
        return first.url if first else None

    def is_user_attending(self, user):
        if user.is_authenticated:
            return self.attendees.filter(user=user).exists()
        return False


class EventSource(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="sources")
    url = models.URLField(max_length=2000)
    source_name = models.CharField(max_length=200)
    external_id = models.CharField(max_length=300, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_sources"
        unique_together = ("event", "url")
        indexes = [
            models.Index(fields=["event", "-added_at"]),
            models.Index(fields=["source_name"]),
        ]

    def __str__(self):
        return f"{self.source_name} → {self.event.canonical_title[:50]}"


class EventAttendee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendees")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="joined_events",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_attendees"
        unique_together = ("event", "user")
        ordering = ["-joined_at"]
        indexes = [
            models.Index(fields=["event", "user"]),
            models.Index(fields=["user", "-joined_at"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.event.title[:50]}"
