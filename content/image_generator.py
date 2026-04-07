# content/image_generator.py - Stock image lookup via Unsplash/Pexels with Django cache

import os
import re
import logging
from typing import Optional

from django.core.cache import cache

from .constants import IMAGE_CATEGORY_QUERIES
from .utils import get_http_session

logger = logging.getLogger(__name__)

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

IMAGE_CACHE_TIMEOUT = 86400  # 24 hours


def extract_keywords(text: str, max_keywords: int = 3) -> str:
    """Extract meaningful keywords from title for image search."""
    stop_words = {
        "the", "is", "at", "which", "on", "a", "an", "and", "or", "but",
        "in", "with", "to", "for", "of", "as", "by", "from", "this", "that",
        "are", "was", "were", "been", "be", "have", "has", "had", "do", "does",
        "did", "will", "would", "should", "could", "may", "might", "can",
        "says", "say", "said", "new", "over", "after", "amid", "how", "why",
        "what", "when", "where", "who", "about", "into", "through", "during",
    }
    text = re.sub(r"[^\w\s]", " ", text.lower())
    words = text.split()
    keywords = [w for w in words if len(w) > 3 and w not in stop_words][:max_keywords]
    if not keywords:
        keywords = [w for w in words[:2] if w not in stop_words]
    return " ".join(keywords[:max_keywords])


def _cached_image_search(cache_prefix: str, query: str, fetcher) -> Optional[str]:
    """Generic cached image lookup. Avoids duplicate cache logic."""
    cache_key = f"img:{cache_prefix}:{query}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached if cached != "" else None

    result = fetcher(query)
    cache.set(cache_key, result or "", IMAGE_CACHE_TIMEOUT)
    return result


def _fetch_unsplash(query: str) -> Optional[str]:
    if not UNSPLASH_ACCESS_KEY or UNSPLASH_ACCESS_KEY == "your_unsplash_access_key_here":
        return None
    try:
        session = get_http_session()
        resp = session.get(
            "https://api.unsplash.com/search/photos",
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            params={"query": query, "per_page": 1, "orientation": "landscape", "content_filter": "high"},
            timeout=5,
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                return results[0]["urls"]["regular"]
        else:
            logger.warning(f"Unsplash API error {resp.status_code}")
    except Exception as e:
        logger.error(f"Unsplash API error: {e}")
    return None


def _fetch_pexels(query: str) -> Optional[str]:
    if not PEXELS_API_KEY or PEXELS_API_KEY == "your_pexels_api_key_here":
        return None
    try:
        session = get_http_session()
        resp = session.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=5,
        )
        if resp.status_code == 200:
            photos = resp.json().get("photos", [])
            if photos:
                return photos[0]["src"]["large"]
        else:
            logger.warning(f"Pexels API error {resp.status_code}")
    except Exception as e:
        logger.error(f"Pexels API error: {e}")
    return None


def get_image_from_unsplash(query: str) -> Optional[str]:
    return _cached_image_search("unsplash", query, _fetch_unsplash)


def get_image_from_pexels(query: str) -> Optional[str]:
    return _cached_image_search("pexels", query, _fetch_pexels)


def generate_image_for_title(title: str) -> Optional[str]:
    """Generate a relevant image URL for a title using stock photo APIs."""
    keywords = extract_keywords(title)
    if not keywords:
        return None

    return get_image_from_unsplash(keywords) or get_image_from_pexels(keywords)


def generate_category_image(category: str) -> Optional[str]:
    """Generate image for a content category."""
    query = IMAGE_CATEGORY_QUERIES.get(category.lower(), IMAGE_CATEGORY_QUERIES["default"])
    return get_image_from_unsplash(query) or get_image_from_pexels(query)


def detect_category(title: str) -> str:
    """Quick category detection from title for image matching.
    Delegates to CategoryClassifier for consistency.
    """
    from .services import CategoryClassifier
    result = CategoryClassifier.classify_content(title)
    return result[0] if result else "default"
