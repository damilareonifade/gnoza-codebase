import re
from typing import Optional
from urllib.parse import urlparse
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from content.models import ContentCluster
from .source import ClusterSourceSerializer, _PLACEHOLDER


def _clean_summary(text: str) -> str:
    if not text or not text.strip():
        return ""
    return " ".join(line.strip() for line in text.split("\n") if line.strip()).strip()


class ContentClusterSerializer(serializers.ModelSerializer):
    sources = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    img_url = serializers.SerializerMethodField()
    source_logo = serializers.SerializerMethodField()
    snippet = serializers.SerializerMethodField()
    full_text = serializers.SerializerMethodField()
    has_full_text = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()
    is_fresh = serializers.SerializerMethodField()
    is_breaking = serializers.SerializerMethodField()
    short_summary = serializers.SerializerMethodField()
    medium_summary = serializers.SerializerMethodField()
    long_summary = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()
    user_has_liked = serializers.SerializerMethodField()
    relevance_score = serializers.FloatField(read_only=True, default=0.0)

    class Meta:
        model = ContentCluster
        fields = [
            "id", "canonical_title", "canonical_url", "image_url",
            "primary_image", "img_url", "source_logo",
            "snippet", "short_summary", "medium_summary", "long_summary",
            "synthesis", "key_points", "categories", "keywords",
            "trend_score", "importance_score", "freshness_score",
            "persistence_score", "quality_score", "source_count", "views",
            "first_seen_at", "last_updated_at", "sources", "relevance_score",
            "is_fresh", "is_breaking", "has_full_text", "full_text",
            "content_type", "total_likes", "user_has_liked",
        ]

    # ---- summaries -------------------------------------------------------

    def get_short_summary(self, obj) -> str:
        s = _clean_summary(obj.short_summary)
        if not s or len(s) < 80:
            fallback = f"{obj.canonical_title}. {obj.merged_snippet}"
            return fallback[:250] if obj.merged_snippet else f"{obj.canonical_title} - Latest updates."
        return s

    def get_medium_summary(self, obj) -> str:
        s = _clean_summary(obj.medium_summary)
        if not s or len(s) < 150:
            if obj.merged_snippet and len(obj.merged_snippet) >= 150:
                return f"{obj.canonical_title}. {obj.merged_snippet}"[:600]
            return (
                f"{obj.canonical_title}. "
                f"{obj.merged_snippet or 'Stay informed with the latest developments.'} "
                "Follow for comprehensive coverage."
            )
        return s

    def get_long_summary(self, obj) -> str:
        s = _clean_summary(obj.long_summary)
        if not s or len(s) < 400:
            base = f"{obj.canonical_title}. {obj.merged_snippet or 'This is a developing story.'}"
            if len(base) < 400:
                base += (
                    " Our team is monitoring this situation closely and will provide "
                    "comprehensive updates as more information emerges."
                )
            return base[:1500]
        return s

    # ---- sources ---------------------------------------------------------

    def get_sources(self, obj) -> list:
        seen_domains = set()
        unique = []
        for source in obj.sources.select_related("raw_content").order_by(
            "-credibility_score", "-added_at"
        ):
            try:
                domain = urlparse(source.url).netloc.lower().replace("www.", "").split(":")[0]
            except Exception:
                domain = source.url
            if domain not in seen_domains:
                seen_domains.add(domain)
                unique.append(source)
        return ClusterSourceSerializer(unique, many=True).data

    # ---- images ----------------------------------------------------------

    def get_primary_image(self, obj) -> Optional[str]:
        if obj.image_url:
            return obj.image_url
        for source in obj.sources.all():
            if source.raw_content and source.raw_content.image_url:
                return source.raw_content.image_url
        if any("reddit.com" in s.url.lower() for s in obj.sources.all()):
            return "https://www.redditinc.com/assets/images/site/reddit-logo.png"
        return _PLACEHOLDER

    def get_img_url(self, obj) -> str:
        return self.get_primary_image(obj) or _PLACEHOLDER

    def get_source_logo(self, obj) -> Optional[str]:
        primary = obj.sources.order_by("-credibility_score", "-added_at").first()
        if not primary:
            return None
        return ClusterSourceSerializer().get_logo(primary)

    # ---- content type ---------------------------------------------------

    def get_content_type(self, obj) -> str:
        forced = self.context.get("force_content_type")
        if forced:
            return forced

        prefetched = getattr(obj, "_prefetched_objects_cache", {}) or {}
        sources = prefetched.get("sources")
        if sources is not None:
            has_yt = any(
                s.raw_content and getattr(s.raw_content, "source_type", "") == "youtube"
                for s in sources
            )
        else:
            has_yt = obj.sources.filter(raw_content__source_type="youtube").exists()

        if has_yt:
            return "youtube"

        ct = (getattr(obj, "content_type", "") or "").upper()
        if ct == "EVENT" or getattr(obj, "is_event", False):
            return "event"
        if ct == "ARTICLE":
            return "articles"
        return "news"

    # ---- text ------------------------------------------------------------

    def get_full_text(self, obj) -> str:
        if hasattr(obj, "get_full_text"):
            return obj.get_full_text()
        return obj.canonical_title or "Content unavailable"

    def get_snippet(self, obj) -> str:
        text = (
            getattr(obj, "short_summary", "") or
            getattr(obj, "medium_summary", "") or
            getattr(obj, "long_summary", "") or
            self.get_full_text(obj) or ""
        ).strip()
        return (text[:197] + "...") if len(text) > 200 else text

    def get_has_full_text(self, obj) -> bool:
        if getattr(obj, "long_summary", None) or getattr(obj, "medium_summary", None):
            return True
        for source in obj.sources.all():
            raw = getattr(source, "raw_content", None)
            if raw and (raw.full_text or raw.snippet):
                return True
        return bool(obj.canonical_title)

    # ---- flags ----------------------------------------------------------

    def get_is_fresh(self, obj) -> bool:
        return (timezone.now() - obj.first_seen_at).total_seconds() / 3600 < 6

    def get_is_breaking(self, obj) -> bool:
        return (
            obj.source_count >= 4
            and obj.trend_score > 0.75
            and self.get_is_fresh(obj)
        )

    # ---- social ---------------------------------------------------------

    def get_total_likes(self, obj) -> int:
        if hasattr(obj, "total_likes"):
            return obj.total_likes
        return obj.likes.count()

    def get_user_has_liked(self, obj) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()

    # ---- to_representation ---------------------------------------------

    def to_representation(self, instance):
        if instance.source_count < 1:
            return None
        data = super().to_representation(instance)
        if data and "sources" in data and data["sources"]:
            seen = set()
            unique = []
            for src in data["sources"]:
                try:
                    domain = urlparse(src.get("url", "")).netloc.lower().replace("www.", "").split(":")[0]
                except Exception:
                    domain = None
                if domain and domain not in seen:
                    seen.add(domain)
                    unique.append(src)
                elif not domain:
                    unique.append(src)
            data["sources"] = unique
            data["source_count"] = len(unique)
            if not unique:
                return None
        return data
