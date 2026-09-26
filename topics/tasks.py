import logging

from celery import shared_task
from django.contrib.auth import get_user_model

from .services import (
    ensure_category_topics,
    get_trending_categories,
    refresh_user_preferred_topics,
    update_popular_topics,
)

logger = logging.getLogger(__name__)


@shared_task(name="topics.tasks.refresh_preferred_topics")
def refresh_preferred_topics():
    """Re-rank topics from the latest news and refresh every active user's preferred_topics."""
    ensure_category_topics()
    trending = get_trending_categories(use_cache=False)
    update_popular_topics(trending)

    updated = 0
    for user in get_user_model().objects.filter(is_active=True).iterator():
        try:
            refresh_user_preferred_topics(user, trending=trending)
            updated += 1
        except Exception as exc:
            logger.warning(f"Preferred topics refresh failed for {user.pk}: {exc}")

    logger.info(f"Refreshed preferred topics for {updated} users (trending={trending[:5]})")
    return {"users": updated, "trending": trending}
