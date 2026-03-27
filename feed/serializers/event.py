from django.utils import timezone
from rest_framework import serializers

from content.models import Event

_PLACEHOLDER = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/640px-No_image_available.svg.png"


class EventSerializer(serializers.ModelSerializer):
    content_type = serializers.SerializerMethodField()
    img_url = serializers.SerializerMethodField()
    full_text = serializers.SerializerMethodField()
    attendee_count = serializers.IntegerField(read_only=True)
    is_user_attending = serializers.SerializerMethodField()
    title = serializers.CharField(source="canonical_title")
    sources = serializers.SerializerMethodField()
    short_summary = serializers.SerializerMethodField()
    medium_summary = serializers.SerializerMethodField()
    long_summary = serializers.SerializerMethodField()
    event_url = serializers.CharField(read_only=True)
    attendees = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "title", "canonical_title", "description",
            "short_summary", "medium_summary", "long_summary",
            "image_url", "img_url", "start_time", "end_time",
            "venue_name", "location_name", "latitude", "longitude",
            "categories", "keywords", "source_count", "fetched_at",
            "content_type", "full_text", "attendee_count",
            "is_user_attending", "attendees", "event_url", "sources",
        ]

    def get_content_type(self, obj):
        return "event"

    def get_img_url(self, obj):
        return obj.image_url or _PLACEHOLDER

    def get_short_summary(self, obj):
        if obj.short_summary and len(obj.short_summary) >= 50:
            return obj.short_summary
        return f"{obj.canonical_title} at {obj.location_name} on {obj.start_time.strftime('%B %d, %Y')}"

    def get_medium_summary(self, obj):
        if obj.medium_summary and len(obj.medium_summary) >= 100:
            return obj.medium_summary
        venue = obj.venue_name or obj.location_name
        date = obj.start_time.strftime("%B %d")
        if obj.description and len(obj.description) > 50:
            return f"{obj.canonical_title} at {venue} on {date}. {obj.description[:200]}..."
        return f"{obj.canonical_title} is happening at {venue} in {obj.location_name} on {obj.start_time.strftime('%B %d, %Y at %I:%M %p')}."

    def get_long_summary(self, obj):
        if obj.long_summary and len(obj.long_summary) >= 200:
            return obj.long_summary
        summary = (
            f"{obj.canonical_title} is taking place at "
            f"{obj.venue_name or obj.location_name} in {obj.location_name} on "
            f"{obj.start_time.strftime('%B %d, %Y at %I:%M %p')}."
        )
        if obj.description:
            summary += f" {obj.description}"
        else:
            cat = obj.categories[0] if obj.categories else "special"
            summary += f" This is a {cat} event. Mark your calendar and get your tickets early."
        return summary

    def get_is_user_attending(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.is_user_attending(request.user)
        return False

    def get_attendees(self, obj):
        from accounts.serializers import UserMiniSerializer
        attendees = obj.attendees.select_related("user").all()[:50]
        return [
            {"id": str(a.user.id), "email": a.user.email, "display": str(a.user)}
            for a in attendees
        ]

    def get_sources(self, obj):
        return [
            {"url": s.url, "source_name": s.source_name, "external_id": s.external_id}
            for s in obj.sources.all()
        ]

    def get_full_text(self, obj):
        parts = [f"Event: {obj.canonical_title}"]
        parts.append(f"Description: {obj.description}" if obj.description else "Description: No description available")
        if obj.venue_name:
            parts.append(f"Venue: {obj.venue_name}")
        if obj.location_name:
            parts.append(f"Location: {obj.location_name}")
        if obj.start_time:
            local_time = timezone.localtime(obj.start_time)
            parts.append(f"Date: {local_time.strftime('%B %d, %Y at %I:%M %p')}")
        if obj.categories:
            parts.append(f"Categories: {', '.join(filter(None, obj.categories))}")
        if obj.long_summary and obj.long_summary.strip():
            parts.append(f"\nDetails: {obj.long_summary}")
        elif obj.medium_summary and obj.medium_summary.strip():
            parts.append(f"\nDetails: {obj.medium_summary}")
        return "\n".join(parts)
