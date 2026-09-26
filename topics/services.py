import logging
from collections import Counter
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from content.models import ContentCluster, CATEGORY_CHOICES
from .models import Topic, UserTopic

logger = logging.getLogger(__name__)

CATEGORY_SLUGS = [slug for slug, _ in CATEGORY_CHOICES]
PREFERRED_TOPICS_LIMIT = 5
POPULAR_TOPICS_LIMIT = 5
INTERACTION_WINDOW_DAYS = 30
# Widen the news window until some categories show up.
NEWS_WINDOWS_HOURS = (48, 24 * 7, 24 * 30)
DEFAULT_TOPICS = ["national", "international", "business", "technology", "sport"]

TRENDING_CATEGORIES_CACHE_KEY = "topics:trending_categories"
TRENDING_CATEGORIES_CACHE_TTL = 60 * 30


def normalize_topic_slugs(values):
    """Lowercase, dedupe and keep only known category slugs (accepts names or slugs)."""
    seen = []
    for value in values or []:
        slug = str(value).strip().lower()
        if slug in CATEGORY_SLUGS and slug not in seen:
            seen.append(slug)
    return seen


def ensure_category_topics():
    """Make sure every news category exists as a Topic row."""
    existing = set(Topic.objects.values_list("slug", flat=True))
    missing = [
        Topic(name=name, slug=slug, order=index)
        for index, (slug, name) in enumerate(CATEGORY_CHOICES)
        if slug not in existing
    ]
    if missing:
        Topic.objects.bulk_create(missing, ignore_conflicts=True)


def _compute_trending_categories():
    now = timezone.now()
    for hours in NEWS_WINDOWS_HOURS:
        rows = ContentCluster.objects.filter(
            first_seen_at__gte=now - timedelta(hours=hours)
        ).values_list("categories", "source_count", "views")

        scores = Counter()
        for categories, source_count, views in rows.iterator():
            weight = 1 + min(source_count, 10) * 0.5 + min(views, 1000) / 100
            for category in normalize_topic_slugs(categories):
                scores[category] += weight
        if scores:
            return [slug for slug, _ in scores.most_common()]
    return list(DEFAULT_TOPICS)


def get_trending_categories(use_cache=True):
    """Category slugs ranked by how heavily current news covers them."""
    if not use_cache:
        trending = _compute_trending_categories()
        cache.set(TRENDING_CATEGORIES_CACHE_KEY, trending, TRENDING_CATEGORIES_CACHE_TTL)
        return trending
    return cache.get_or_set(
        TRENDING_CATEGORIES_CACHE_KEY,
        _compute_trending_categories,
        TRENDING_CATEGORIES_CACHE_TTL,
    )


def get_interest_categories(user):
    """Category scores from the stories the user recently bookmarked, liked or commented on."""
    from interactions.models import Bookmark, Like, Comment

    cutoff = timezone.now() - timedelta(days=INTERACTION_WINDOW_DAYS)
    scores = Counter()
    for model, weight in ((Bookmark, 3), (Like, 2), (Comment, 2)):
        rows = model.objects.filter(user=user, created_at__gte=cutoff).values_list(
            "cluster__categories", flat=True
        )
        for categories in rows:
            for category in normalize_topic_slugs(categories):
                scores[category] += weight
    return scores


def get_explicit_topics(user):
    """Topics the user picked themselves (onboarding, preferences, topic toggles)."""
    slugs = UserTopic.objects.filter(user=user, is_saved=True).values_list(
        "topic__slug", flat=True
    )
    return normalize_topic_slugs(slugs)


def refresh_user_preferred_topics(user, trending=None):
    """
    Rebuild preferred_topics: the user's own picks first, then fill up to
    PREFERRED_TOPICS_LIMIT with categories from their interactions and current news.
    """
    from accounts.models import UserPreference

    prefs, _ = UserPreference.objects.get_or_create(user=user)
    explicit = get_explicit_topics(user)
    interests = get_interest_categories(user)
    trending = trending if trending is not None else get_trending_categories()
    trend_rank = {slug: len(trending) - index for index, slug in enumerate(trending)}

    candidates = sorted(
        (
            slug for slug in CATEGORY_SLUGS
            if slug not in explicit and (slug in interests or slug in trend_rank)
        ),
        key=lambda slug: (interests.get(slug, 0), trend_rank.get(slug, 0)),
        reverse=True,
    )
    topics = explicit + candidates[: max(0, PREFERRED_TOPICS_LIMIT - len(explicit))]

    if topics != prefs.preferred_topics:
        prefs.preferred_topics = topics
        prefs.save(update_fields=["preferred_topics", "updated_at"])
    return topics


def set_explicit_topics(user, values):
    """Replace the topics the user picked themselves, then refresh preferred_topics."""
    ensure_category_topics()
    topics = list(Topic.objects.filter(slug__in=normalize_topic_slugs(values)))
    with transaction.atomic():
        UserTopic.objects.filter(user=user).exclude(topic__in=topics).update(is_saved=False)
        for topic in topics:
            UserTopic.objects.update_or_create(
                user=user, topic=topic, defaults={"is_saved": True}
            )
    return refresh_user_preferred_topics(user)


def update_popular_topics(trending):
    """Flag and order Topic rows by how much the news is covering them right now."""
    rank = {slug: index for index, slug in enumerate(trending)}
    popular = set(trending[:POPULAR_TOPICS_LIMIT])
    for topic in Topic.objects.filter(slug__in=CATEGORY_SLUGS):
        order = rank.get(topic.slug, len(CATEGORY_SLUGS))
        is_popular = topic.slug in popular
        if topic.order != order or topic.is_popular != is_popular:
            topic.order = order
            topic.is_popular = is_popular
            topic.save(update_fields=["order", "is_popular", "updated_at"])
