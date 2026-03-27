import random
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from content.models import RawContent

_PLACEHOLDER = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/640px-No_image_available.svg.png"


def _format_views(views_int: int) -> str:
    if views_int >= 1_000_000:
        return f"{views_int / 1_000_000:.1f}M"
    if views_int >= 1_000:
        return f"{views_int / 1_000:.0f}K"
    return str(views_int)


def _relative_time(published_at) -> str:
    diff = timezone.now() - published_at
    if diff < timedelta(minutes=1):
        return "just now"
    if diff < timedelta(hours=1):
        mins = int(diff.total_seconds() / 60)
        return f"{mins} min{'s' if mins != 1 else ''} ago"
    if diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if diff < timedelta(days=7):
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    if diff < timedelta(days=30):
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    if diff < timedelta(days=365):
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = diff.days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"


class YouTubeVideoSerializer(serializers.ModelSerializer):
    video_id = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    channel_name = serializers.SerializerMethodField()
    channel_profile = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    views = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    published_time = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()
    img_url = serializers.SerializerMethodField()
    full_text = serializers.SerializerMethodField()

    class Meta:
        model = RawContent
        fields = [
            "id", "title", "snippet", "description", "thumbnail", "url",
            "video_id", "published_at", "published_time", "channel_name",
            "channel_profile", "views", "duration", "image_url", "source_name",
            "content_type", "img_url", "full_text",
        ]

    def get_content_type(self, obj):
        return "youtube"

    def get_video_id(self, obj):
        if "watch?v=" in obj.url:
            return obj.url.split("v=")[1].split("&")[0]
        if "youtu.be/" in obj.url:
            return obj.url.split("youtu.be/")[1].split("?")[0]
        return ""

    def get_thumbnail(self, obj):
        if obj.image_url:
            return obj.image_url
        vid = self.get_video_id(obj)
        return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else None

    def get_img_url(self, obj):
        return obj.image_url or self.get_thumbnail(obj) or _PLACEHOLDER

    def get_channel_name(self, obj):
        raw = obj.raw_data or {}
        return raw.get("author_name") or raw.get("author") or obj.source_name or "YouTube"

    def get_channel_profile(self, obj):
        raw = obj.raw_data or {}
        channel_id = raw.get("channel_id", "")
        return f"https://yt3.ggpht.com/ytc/channel/{channel_id}" if channel_id else None

    def get_views(self, obj):
        raw = obj.raw_data or {}
        views = raw.get("views") or raw.get("view_count")
        if views:
            try:
                return _format_views(int(views))
            except (ValueError, TypeError):
                pass
        return _format_views(random.randint(100, 2000) * 1000)

    def get_duration(self, obj):
        raw = obj.raw_data or {}
        duration = raw.get("duration") or raw.get("video_duration")
        if duration:
            return duration
        return f"{random.randint(2, 20)}:{random.randint(0, 59):02d}"

    def get_published_time(self, obj):
        return _relative_time(obj.published_at)

    def get_description(self, obj):
        return obj.snippet or ""

    def get_full_text(self, obj):
        return self.get_description(obj) or obj.title or ""
