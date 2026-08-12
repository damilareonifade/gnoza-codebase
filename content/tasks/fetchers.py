# content/tasks/fetchers.py - All content source fetcher tasks

import json
import time
import logging
from datetime import timedelta

import requests
import feedparser
import praw
from bs4 import BeautifulSoup
from django.db import models
from django.utils import timezone
from django.conf import settings
from dateutil import parser as date_parser
from celery import shared_task
import google.generativeai as genai

from content.models import RawContent, ContentCluster, ClusterSource
from content.services import find_or_create_cluster, CategoryClassifier
from content.image_generator import generate_image_for_title, detect_category, generate_category_image
from content.utils import (
    clean_url, parse_published_date, extract_full_text_and_image,
    extract_image_from_raw_data, get_http_session, parse_date_string,
)
from content.constants import (
    YOUTUBE_CHANNEL_MAP, TOPIC_TO_CHANNEL_KEYS, DEFAULT_TOPICS,
)
from accounts.models import UserPreference

logger = logging.getLogger(__name__)

# Lazy Gemini model
_gemini_model = None


def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-2.5-pro")
    return _gemini_model


def get_personalized_topics() -> list[str]:
    """Get personalized topics from user preferences."""
    topics = set()
    for pref in UserPreference.objects.filter(onboarding_completed=True).only("preferred_topics"):
        topics.update(t.lower() for t in pref.preferred_topics)
    if len(topics) < 3:
        topics.update([
            "technology", "science", "business", "health", "world news",
            "politics", "sports", "climate change", "artificial intelligence", "nigeria",
        ])
    return list(topics)


# ==========================================
# NEWSAPI
# ==========================================
@shared_task(name='content.tasks.fetch_newsapi_articles', bind=True, max_retries=2, default_retry_delay=60)
def fetch_newsapi_articles(self):
    """Fetch articles from NewsAPI with personalization."""
    if not settings.NEWSAPI_KEY:
        logger.error("NEWSAPI_KEY missing")
        return 0

    session = get_http_session()
    headers = {"X-Api-Key": settings.NEWSAPI_KEY}
    topics = get_personalized_topics() or ["nigeria", "africa", "technology", "business", "politics"]
    fetched = 0

    for topic in topics[:12]:
        params = {
            "q": topic,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
            "from": (timezone.now() - timedelta(hours=72)).isoformat(),
        }

        try:
            resp = session.get(
                "https://newsapi.org/v2/everything",
                headers=headers, params=params, timeout=20,
            )
            if resp.status_code == 401:
                logger.error("[NewsAPI] Authentication failed")
                return 0
            if resp.status_code == 429:
                logger.warning("[NewsAPI] Rate limit hit")
                break
            if resp.status_code != 200:
                logger.warning(f"[NewsAPI] {topic}: HTTP {resp.status_code}")
                continue

            for art in resp.json().get("articles", []):
                url = art.get("url")
                if not url or RawContent.objects.filter(url=url).exists():
                    continue

                published_at = timezone.now()
                if art.get("publishedAt"):
                    try:
                        published_at = date_parser.isoparse(art["publishedAt"])
                        if published_at.tzinfo is None:
                            published_at = timezone.make_aware(published_at)
                    except Exception:
                        pass

                raw = RawContent.objects.create(
                    source_type="newsapi",
                    source_name=art.get("source", {}).get("name", "NewsAPI"),
                    url=url,
                    title=art.get("title", "No title")[:600],
                    snippet=(art.get("description") or "")[:500],
                    image_url=art.get("urlToImage"),
                    published_at=published_at,
                    raw_data=art,
                )
                from content.tasks.processing import process_raw_content
                process_raw_content.delay(raw.id)
                fetched += 1

        except Exception as e:
            logger.error(f"[NewsAPI] Error on topic '{topic}': {e}")

    logger.info(f"[NewsAPI] COMPLETE: {fetched} new articles")
    return fetched


# ==========================================
# THE GUARDIAN
# ==========================================
@shared_task(name='content.tasks.fetch_guardian_articles', bind=True, max_retries=2, default_retry_delay=60)
def fetch_guardian_articles(self):
    """Fetch articles from The Guardian API."""
    if not settings.GUARDIAN_API_KEY:
        return 0

    session = get_http_session()
    fetched = 0
    params = {
        "api-key": settings.GUARDIAN_API_KEY,
        "page-size": 20,
        "show-fields": "headline,trailText,bodyText,thumbnail",
        "from-date": (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "order-by": "newest",
    }

    try:
        resp = session.get("https://content.guardianapis.com/search", params=params, timeout=15)
        if resp.status_code != 200:
            return 0

        for art in resp.json().get("response", {}).get("results", []):
            url = art.get("webUrl")
            if not url or RawContent.objects.filter(url=url).exists():
                continue

            fields = art.get("fields", {})
            raw = RawContent.objects.create(
                source_type="guardian",
                source_name="The Guardian",
                url=url,
                title=art.get("webTitle", "No title"),
                snippet=fields.get("trailText", "")[:500],
                image_url=fields.get("thumbnail"),
                published_at=art.get("webPublicationDate") or timezone.now(),
                raw_data=art,
            )
            from content.tasks.processing import process_raw_content
            process_raw_content.delay(raw.id)
            fetched += 1
    except Exception as e:
        logger.error(f"Guardian API error: {e}")

    logger.info(f"[Guardian] {fetched} articles fetched")
    return fetched


# ==========================================
# RSS FEEDS
# ==========================================
@shared_task(name='content.tasks.fetch_rss_feeds', bind=True, max_retries=2, default_retry_delay=60)
def fetch_rss_feeds(self):
    """Fetch articles from configured RSS feeds."""
    fetched = 0
    feed_list = list(settings.RSS_FEEDS.items())

    if UserPreference.objects.filter(onboarding_completed=True, preferred_locations__contains="Nigeria").exists():
        nigerian_keys = [k for k in settings.RSS_FEEDS if "africa" in k.lower() or "nigeria" in k.lower()]
        feed_list = sorted(feed_list, key=lambda x: 0 if x[0] in nigerian_keys else 1)

    for name, url in feed_list:
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                logger.warning(f"RSS parse failed: {name}")
                continue

            for entry in feed.entries[:20]:
                link = entry.get("link") or entry.get("id")
                if not link or RawContent.objects.filter(url=link).exists():
                    continue

                image_url = None
                if "media_content" in entry and entry.media_content:
                    image_url = entry.media_content[0].get("url")
                elif "enclosures" in entry and entry.enclosures:
                    image_url = entry.enclosures[0].get("url")

                raw = RawContent.objects.create(
                    source_type="rss",
                    source_name=name,
                    url=link,
                    title=entry.get("title", "No title"),
                    snippet=entry.get("summary", "")[:500],
                    image_url=image_url,
                    published_at=parse_published_date(entry),
                    raw_data=dict(entry),
                )
                from content.tasks.processing import process_raw_content
                process_raw_content.delay(raw.id)
                fetched += 1
        except Exception as e:
            logger.error(f"RSS error ({name}): {e}")

    logger.info(f"[RSS] {fetched} new items")
    return fetched


# ==========================================
# REDDIT
# ==========================================
@shared_task(name='content.tasks.fetch_reddit_posts', bind=True, max_retries=2, default_retry_delay=60)
def fetch_reddit_posts(self):
    """Fetch posts from Reddit with AI-powered image generation fallback."""
    if not all([settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET]):
        logger.error("Reddit credentials missing")
        return 0

    fetched = 0
    reddit = praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT or "GnozaAI/1.0",
    )

    subreddits = ["worldnews", "news", "technology", "science", "politics", "nigeria", "africa"]

    for sub in subreddits:
        try:
            for submission in reddit.subreddit(sub).hot(limit=12):
                url = submission.url
                if RawContent.objects.filter(url=url).exists():
                    continue
                if submission.is_self and not submission.selftext:
                    continue

                image_url = None
                if submission.thumbnail and submission.thumbnail not in ("self", "default", "nsfw", "spoiler"):
                    image_url = submission.thumbnail

                if not image_url:
                    image_url = generate_image_for_title(submission.title)
                if not image_url:
                    category = detect_category(submission.title)
                    image_url = generate_category_image(category)

                raw = RawContent.objects.create(
                    source_type="reddit",
                    source_name=f"r/{sub}",
                    url=url,
                    title=submission.title,
                    snippet=submission.selftext[:500] if submission.is_self else submission.title[:500],
                    full_text=submission.selftext if submission.is_self else "",
                    image_url=image_url,
                    published_at=timezone.now(),
                    raw_data={
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "permalink": submission.permalink,
                    },
                )
                from content.tasks.processing import process_raw_content
                process_raw_content.delay(raw.id)
                fetched += 1
        except Exception as e:
            logger.error(f"Reddit error r/{sub}: {e}")

    logger.info(f"[Reddit] {fetched} posts fetched")
    return fetched


# ==========================================
# YOUTUBE
# ==========================================
@shared_task(name='content.tasks.fetch_youtube_recommendations', bind=True, max_retries=2, default_retry_delay=60)
def fetch_youtube_recommendations(self):
    """Fetch personalized YouTube videos from reliable channels via RSS."""
    fetched = 0
    users = UserPreference.objects.filter(onboarding_completed=True).only(
        "user_id", "preferred_topics", "preferred_locations",
    )

    for pref in users:
        if not pref.preferred_topics:
            continue

        channel_ids = set()
        topics_lower = [t.lower() for t in pref.preferred_topics]

        # Map topics to channel groups
        for topic in topics_lower:
            for base_key in TOPIC_TO_CHANNEL_KEYS.get(topic, []):
                channel_ids.update(YOUTUBE_CHANNEL_MAP.get(base_key, []))
            for key, ids in YOUTUBE_CHANNEL_MAP.items():
                if key in topic:
                    channel_ids.update(ids)

        # Location-based boosts
        locations_lower = [loc.lower() for loc in (pref.preferred_locations or [])]
        user_country = _detect_user_country(locations_lower, topics_lower, channel_ids)

        if not channel_ids:
            continue

        for channel_id in channel_ids:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            try:
                feed = feedparser.parse(rss_url)
                if feed.bozo:
                    continue

                for entry in feed.entries[:10]:
                    video_id = entry.id.split(":")[-1]
                    if RawContent.objects.filter(external_id=video_id, source_type="youtube").exists():
                        continue

                    thumbnail = ""
                    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                        thumbnail = entry.media_thumbnail[0]["url"]

                    raw_data = dict(entry)
                    raw_data["user_country"] = user_country
                    raw_data["channel_id"] = channel_id

                    RawContent.objects.create(
                        source_type="youtube",
                        source_name="YouTube",
                        external_id=video_id,
                        url=entry.link,
                        title=entry.title,
                        snippet=(entry.summary[:500] if hasattr(entry, "summary") else entry.title),
                        image_url=thumbnail,
                        published_at=date_parser.parse(entry.published),
                        raw_data=raw_data,
                        processed=False,
                    )
                    fetched += 1
            except Exception as e:
                logger.error(f"YouTube fetch failed for channel {channel_id}: {e}")

    logger.info(f"[YouTube] {fetched} videos fetched")
    return fetched


def _detect_user_country(locations_lower, topics_lower, channel_ids):
    """Detect user's primary country and boost channel_ids accordingly."""
    user_country = None

    country_configs = [
        {
            "keywords": ["nigeria", "lagos", "abuja", "ng"],
            "country": "nigeria",
            "always_add": ["nigeria"],
            "sports_add": ["nigeria_sports"],
            "intl_add": ["world_news", "uk", "us"],
        },
        {
            "keywords": ["uk", "united kingdom", "england", "london"],
            "country": "uk",
            "always_add": ["uk", "world_news"],
            "sports_add": [],
            "intl_add": ["us", "nigeria"],
        },
        {
            "keywords": ["us", "usa", "united states", "america"],
            "country": "us",
            "always_add": ["us", "world_news"],
            "sports_add": [],
            "intl_add": ["uk", "nigeria"],
        },
    ]

    for cfg in country_configs:
        if any(loc in locations_lower for loc in cfg["keywords"]):
            user_country = cfg["country"]
            for key in cfg["always_add"]:
                channel_ids.update(YOUTUBE_CHANNEL_MAP.get(key, []))
            if any(t in topics_lower for t in ("sports", "sport")):
                for key in cfg["sports_add"]:
                    channel_ids.update(YOUTUBE_CHANNEL_MAP.get(key, []))
            if any(t in topics_lower for t in ("international", "world")):
                for key in cfg["intl_add"]:
                    channel_ids.update(list(YOUTUBE_CHANNEL_MAP.get(key, []))[:5])
            break

    return user_country


# ==========================================
# NIGERIAN NEWSPAPERS
# ==========================================
@shared_task(name='content.tasks.fetch_nigerian_newspapers', bind=True, max_retries=2, default_retry_delay=60)
def fetch_nigerian_newspapers(self):
    """Scrape Nigerian newspaper homepages for articles."""
    fetched = 0
    session = get_http_session()

    for name, config in settings.NIGERIAN_NEWS_SOURCES.items():
        try:
            resp = session.get(config["homepage"], timeout=20)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.select(config["article_selector"])[:20]

            for art in articles:
                link_tag = art.select_one(config.get("link_selector") or "a")
                if not link_tag or not link_tag.get("href"):
                    continue
                from urllib.parse import urljoin
                article_url = urljoin(config["homepage"], link_tag["href"])
                if RawContent.objects.filter(url=article_url).exists():
                    continue

                raw = RawContent.objects.create(
                    source_type="scraped",
                    source_name=name,
                    url=article_url,
                    title=art.get_text(strip=True) or "No title",
                    snippet="",
                    image_url=None,
                    published_at=timezone.now(),
                )
                from content.tasks.processing import process_raw_content
                process_raw_content.delay(raw.id)
                fetched += 1
        except Exception as e:
            logger.error(f"Nigerian scraper error ({name}): {e}")

    logger.info(f"[Nigerian newspapers] {fetched} articles")
    return fetched


# ==========================================
# GEMINI MULTI-SOURCE
# ==========================================
def _gemini_search_articles(query: str, num_sources: int = 12) -> list[dict]:
    """Use Gemini to search the web and return diverse articles."""
    prompt = f"""You are an expert news curator with live web access. Search the internet right now for the most important, recent, and diverse coverage on: "{query}"

Return EXACTLY {num_sources} articles from DIFFERENT reputable publishers.

Requirements:
- Only established news outlets: BBC News, Reuters, The Guardian, Al Jazeera, AP News, New York Times, CNN, Bloomberg
- Prioritize Nigerian/African sources when relevant: Punch Nigeria, Vanguard, Daily Trust, Premium Times, ThisDay, Channels Television, The Nation Nigeria, Leadership
- Diverse perspectives and angles
- Prefer articles from the last 48 hours
- NO blogs, YouTube, social media, forums, paywalled content, or low-credibility sites

Each article must include:
{{
  "title": "Exact headline from the article",
  "url": "Full direct URL to the article",
  "source": "Publisher name only",
  "published": "Relative time or ISO date",
  "snippet": "The first 2-3 sentences of the article",
  "full_text": "The complete article body text (aim for 1000+ words)"
}}

Return ONLY a valid JSON array with exactly {num_sources} items. No markdown, no explanations."""

    try:
        model = _get_gemini_model()
        response = model.generate_content(prompt)
        text = response.text.strip()

        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        results = json.loads(text)
        if not isinstance(results, list) or not results:
            return []

        logger.info(f"[Gemini] Retrieved {len(results)} articles for: {query}")
        return results

    except json.JSONDecodeError as e:
        logger.error(f"[Gemini] JSON parse error: {e}")
        return []
    except Exception as e:
        logger.error(f"[Gemini] Failed for '{query}': {type(e).__name__}: {e}")
        return []


@shared_task(name='content.tasks.gemini_multi_source_fetch', bind=True, max_retries=1, default_retry_delay=120)
def gemini_multi_source_fetch(self):
    """Primary content engine: Gemini AI multi-source news aggregation."""
    user_topics = get_personalized_topics()
    all_topics = list(dict.fromkeys(user_topics + DEFAULT_TOPICS))[:15]

    total_fetched = 0

    for topic in all_topics:
        articles = _gemini_search_articles(topic, num_sources=12)
        if not articles:
            continue

        for art in articles:
            url = clean_url(art.get("url", ""))
            if not url or not url.startswith("http"):
                continue
            if RawContent.objects.filter(url=url).exists():
                continue

            title = art.get("title", "No title")[:600]
            full_text = (art.get("full_text", "") or "")[:25000]
            snippet = (art.get("snippet", "") or title)[:600]
            source = art.get("source", "Unknown Source")
            published_at = parse_date_string(art.get("published", ""))

            try:
                raw = RawContent.objects.create(
                    source_type="gemini",
                    source_name=source,
                    url=url,
                    title=title,
                    snippet=snippet,
                    full_text=full_text,
                    published_at=published_at,
                    processed=True,
                )

                cluster = find_or_create_cluster(title, snippet, full_text)
                ClusterSource.objects.get_or_create(
                    cluster=cluster,
                    url=url,
                    defaults={
                        "raw_content": raw,
                        "source_name": source,
                        "credibility_score": 0.9,
                    },
                )

                previous_count = cluster.source_count
                cluster.source_count = cluster.sources.count()

                if cluster.source_count >= 5:
                    cluster.importance_score = min(1.0, cluster.importance_score + 0.3)
                    cluster.trend_score = min(1.0, cluster.trend_score + 0.25)
                elif cluster.source_count >= 3:
                    cluster.importance_score = min(1.0, cluster.importance_score + 0.15)
                    cluster.trend_score = min(1.0, cluster.trend_score + 0.1)

                cluster.save()
                total_fetched += 1

            except Exception as e:
                logger.error(f"[Gemini] Failed to save article from {source}: {e}")
                continue

        time.sleep(8)

    logger.info(f"[Gemini] COMPLETE: {total_fetched} articles fetched")
    return total_fetched


# ==========================================
# MISSING CONTENT BACKFILL
# ==========================================
@shared_task(name='content.tasks.fetch_missing_images')
def fetch_missing_images():
    """Backfill missing images for recent content."""
    contents = RawContent.objects.filter(
        image_url__isnull=True,
        url__contains="http",
        fetched_at__gte=timezone.now() - timedelta(days=7),
    ).exclude(
        source_type__in=["reddit"],
    ).order_by("-fetched_at")[:50]

    session = get_http_session()
    updated = 0

    for content in contents:
        if content.raw_data:
            image = extract_image_from_raw_data(content.raw_data, content.url)
            if image:
                content.image_url = image
                content.save(update_fields=["image_url"])
                updated += 1
                continue

        try:
            url = clean_url(content.url)
            if not url.startswith(("http://", "https://")):
                continue
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                content.image_url = clean_url(og_image["content"])
                content.save(update_fields=["image_url"])
                updated += 1
        except Exception:
            pass

    logger.info(f"[Missing images] Updated {updated}/{len(contents)}")
    return updated


@shared_task(name='content.tasks.fetch_missing_full_text')
def fetch_missing_full_text():
    """Backfill missing full text for recent content."""
    contents = RawContent.objects.filter(
        url__contains="http",
        fetched_at__gte=timezone.now() - timedelta(days=7),
    ).filter(
        models.Q(full_text__isnull=True) | models.Q(full_text=""),
    ).exclude(
        source_type__in=["youtube", "reddit", "gemini"],
    ).order_by("-fetched_at")[:30]

    updated = 0
    for content in contents:
        try:
            url = clean_url(content.url)
            if not url.startswith(("http://", "https://")):
                continue

            text, image = extract_full_text_and_image(url)
            if text and len(text.strip()) > 100:
                content.full_text = text.strip()[:15000]
                if image and not content.image_url:
                    content.image_url = image
                content.save(update_fields=["full_text", "image_url"])
                updated += 1
        except Exception as e:
            logger.error(f"Full text failed for {content.url[:60]}: {e}")

    logger.info(f"[Missing full text] Updated {updated}/{len(contents)}")
    return updated
