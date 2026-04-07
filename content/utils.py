# content/utils.py - Shared utilities for URL cleaning, date parsing, text extraction

import re
import logging
from urllib.parse import urlparse, urlunparse
from datetime import timedelta
from difflib import SequenceMatcher

import requests
import trafilatura
from bs4 import BeautifulSoup
from django.utils import timezone
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

_http_session = None


def get_http_session() -> requests.Session:
    """Reusable HTTP session with connection pooling."""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; GnozaAI/1.0)",
        })
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=requests.adapters.Retry(
                total=2, backoff_factor=0.3,
                status_forcelist=[500, 502, 503, 504],
            ),
        )
        _http_session.mount("https://", adapter)
        _http_session.mount("http://", adapter)
    return _http_session


def clean_url(url: str) -> str:
    """Fix common URL corruption issues."""
    if not url:
        return url

    url = url.strip()

    if url.startswith("httpss://"):
        url = url.replace("httpss://", "https://", 1)
    elif url.startswith("httpp://"):
        url = url.replace("httpp://", "http://", 1)
    elif url.startswith("http://http://") or url.startswith("https://https://"):
        url = url.split("://", 1)[1]
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

    url = url.replace(" ", "")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def normalize_url(url: str) -> str:
    """Normalize a URL by stripping tracking params and standardizing scheme."""
    if not url:
        return ""
    parsed = urlparse(url)
    query_params = parsed.query.split("&")
    cleaned = [
        p for p in query_params
        if not p.startswith(("utm_", "fbclid", "gclid", "ref", "share"))
    ]
    scheme = "https" if parsed.scheme.lower() in ("http", "https") else parsed.scheme
    return urlunparse((
        scheme,
        parsed.netloc.lower(),
        parsed.path,
        parsed.params,
        "&".join(cleaned),
        "",
    )).rstrip("/")


def clean_title(title: str) -> str:
    """Strip common headline prefixes and source suffixes."""
    if not title:
        return ""
    title = re.sub(r"^(Breaking|Update|Live|Exclusive)[\s:]+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\|\s*.+$", "", title)
    title = re.sub(r"\s*[-–—]\s*.+$", "", title)
    return title.strip()


def parse_published_date(entry) -> timezone.datetime:
    """Parse published date from a feedparser entry."""
    if hasattr(entry, "published") and entry.published:
        try:
            dt = date_parser.parse(entry.published)
            if dt.tzinfo is None:
                dt = timezone.make_aware(dt)
            return dt
        except Exception:
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            import time as _time
            ts = _time.mktime(entry.updated_parsed)
            return timezone.make_aware(timezone.datetime.fromtimestamp(ts))
        except Exception:
            pass
    return timezone.now()


def parse_date_string(date_str: str, fallback=None) -> timezone.datetime:
    """Parse a date string with fuzzy matching, return fallback on failure."""
    if not date_str:
        return fallback or timezone.now()
    try:
        parsed = date_parser.parse(date_str, fuzzy=True)
        if parsed.tzinfo is None:
            parsed = timezone.make_aware(parsed)
        return parsed
    except Exception:
        return fallback or timezone.now()


def extract_full_text_and_image(url: str) -> tuple[str, str | None]:
    """Download a URL and extract full article text + main image."""
    url = clean_url(url)
    if not url or not url.startswith(("http://", "https://")):
        return "", None

    try:
        downloaded = trafilatura.fetch_url(url, decode=True)
        if not downloaded:
            return "", None

        text = trafilatura.extract(
            downloaded,
            include_images=True,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
            no_fallback=False,
        )

        metadata = trafilatura.extract_metadata(downloaded)
        main_image = clean_url(metadata.image) if metadata and metadata.image else None

        return (text or "").strip(), main_image
    except Exception as e:
        logger.debug(f"Extraction failed for {url}: {e}")
        return "", None


def extract_image_from_raw_data(raw_data: dict, url: str = None) -> str | None:
    """Extract image URL from raw API data with multiple fallback strategies."""
    if not raw_data:
        return None

    # Direct field checks
    for field, accessor in [
        ("urlToImage", lambda d: d.get("urlToImage")),
        ("media_thumbnail", lambda d: d.get("media_thumbnail", [{}])[0].get("url") if d.get("media_thumbnail") else None),
        ("media_content", lambda d: d.get("media_content", [{}])[0].get("url") if d.get("media_content") else None),
        ("enclosures", lambda d: d.get("enclosures", [{}])[0].get("url") if d.get("enclosures") else None),
    ]:
        try:
            result = accessor(raw_data)
            if result:
                return clean_url(result)
        except (IndexError, KeyError, TypeError):
            continue

    # OG image fallback from URL
    if url:
        try:
            session = get_http_session()
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                og_image = soup.find("meta", property="og:image")
                if og_image and og_image.get("content"):
                    return clean_url(og_image["content"])
        except Exception:
            pass

    return None


def extract_key_terms(title: str) -> set:
    """Extract meaningful terms from a title for clustering comparison."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "should", "could", "may", "might", "must", "can", "this",
        "that", "these", "those", "says", "amid", "after", "over",
    }
    words = [w.strip(".,!?()[]{}'\"") for w in title.split()]
    terms = set()
    for w in words:
        w_lower = w.lower()
        if len(w) > 3 and w_lower not in stop_words:
            terms.add(w_lower)
        elif len(w) == 3 or w.isdigit() or (len(w) <= 4 and w and w[0].isupper()):
            terms.add(w_lower)
    return terms


def similarity_ratio(str1: str, str2: str) -> float:
    """Calculate similarity between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def is_video_content(title: str) -> bool:
    indicators = ["youtube", "video", "watch", "shorts", "vlog", "live", "stream", "reaction"]
    title_lower = title.lower()
    return any(ind in title_lower for ind in indicators)
