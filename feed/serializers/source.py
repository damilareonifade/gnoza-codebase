import re
from urllib.parse import urlparse
from rest_framework import serializers

from content.models import ClusterSource

_HARDCODED_LOGOS = {
    "reddit.com": "https://www.redditinc.com/assets/images/site/reddit-logo.png",
    "bbc.co.uk": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/BBC_Logo_2021.svg/640px-BBC_Logo_2021.svg.png",
    "theguardian.com": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/The_Guardian_2018.svg/640px-The_Guardian_2018.svg.png",
    "aljazeera.com": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Al_Jazeera_English.svg/640px-Al_Jazeera_English.svg.png",
    "cnn.com": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/CNN.svg/640px-CNN.svg.png",
    "reuters.com": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Reuters_logo.svg/640px-Reuters_logo.svg.png",
}
_PLACEHOLDER = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/640px-No_image_available.svg.png"


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "").split(":")[0]
    except Exception:
        return ""


def _clean_text(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'\\n+', ' ', text)
    text = re.sub(r'\\r', '', text)
    text = re.sub(r'\\t', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_source_logo(domain: str) -> str | None:
    if not domain:
        return None
    # Google's favicon CDN always resolves to an icon (a generic globe for
    # unknown domains) instead of 404ing like Clearbit does for smaller/
    # regional sources, so this never leaves a broken image.
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"


class ClusterSourceSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    domain = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    snippet = serializers.SerializerMethodField()
    full_text = serializers.SerializerMethodField()
    published_at = serializers.SerializerMethodField()

    class Meta:
        model = ClusterSource
        fields = [
            "source_name", "display_name", "domain", "url",
            "credibility_score", "logo", "title", "snippet",
            "full_text", "published_at",
        ]

    def get_domain(self, obj):
        return _extract_domain(obj.url) or "unknown"

    def get_display_name(self, obj):
        name = obj.source_name or "Unknown"
        if name.startswith("r/"):
            return f"Reddit - {name[2:].replace('_', ' ').title()}"
        if name.lower() in ("youtube", "youtube.com"):
            if obj.raw_content and obj.raw_content.raw_data:
                channel = (
                    obj.raw_content.raw_data.get("author_name")
                    or obj.raw_content.raw_data.get("author")
                )
                if channel:
                    return f"YouTube - {channel}"
            return "YouTube"
        if obj.raw_content and obj.raw_content.source_name:
            actual = obj.raw_content.source_name.strip()
            if actual and actual.lower() not in ("rss", "newsapi", "scraped", "guardian"):
                return actual
        return name.title()

    def get_logo(self, obj):
        domain = _extract_domain(obj.url)
        return (
            _HARDCODED_LOGOS.get(domain)
            or get_source_logo(domain)
            or _PLACEHOLDER
        )

    def _raw(self, obj):
        return getattr(obj, "raw_content", None)

    def get_title(self, obj):
        raw = self._raw(obj)
        return _clean_text(getattr(raw, "title", "") or "") if raw else ""

    def get_snippet(self, obj):
        raw = self._raw(obj)
        if not raw:
            return ""
        text = _clean_text(raw.snippet or raw.full_text or "")
        return text[:197] + "..." if len(text) > 200 else text

    def get_full_text(self, obj):
        raw = self._raw(obj)
        if not raw:
            return ""
        return _clean_text(raw.full_text or raw.snippet or raw.title or "")

    def get_published_at(self, obj):
        raw = self._raw(obj)
        return getattr(raw, "published_at", None) if raw else None
