# content/tasks/__init__.py - Re-exports all Celery tasks for autodiscovery

from .processing import process_raw_content, fetch_full_text_for_cluster
from .summaries import generate_ai_summaries, generate_event_summary
from .fetchers import (
    fetch_newsapi_articles,
    fetch_rss_feeds,
    fetch_reddit_posts,
    fetch_guardian_articles,
    fetch_nigerian_newspapers,
    fetch_youtube_recommendations,
    gemini_multi_source_fetch,
    fetch_missing_images,
    fetch_missing_full_text,
)
from .events import (
    fetch_ticketmaster_events,
    fetch_eventbrite_events,
    fetch_eventbrite_scraped_events,
    fetch_local_nigerian_events,
    cleanup_duplicate_events,
)

__all__ = [
    "process_raw_content",
    "fetch_full_text_for_cluster",
    "generate_ai_summaries",
    "generate_event_summary",
    "fetch_newsapi_articles",
    "fetch_rss_feeds",
    "fetch_reddit_posts",
    "fetch_guardian_articles",
    "fetch_nigerian_newspapers",
    "fetch_youtube_recommendations",
    "gemini_multi_source_fetch",
    "fetch_missing_images",
    "fetch_missing_full_text",
    "fetch_ticketmaster_events",
    "fetch_eventbrite_events",
    "fetch_eventbrite_scraped_events",
    "fetch_local_nigerian_events",
    "cleanup_duplicate_events",
]
