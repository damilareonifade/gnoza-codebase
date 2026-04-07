# content/tasks/processing.py - Raw content processing and full text extraction

import re
import logging
from urllib.parse import urljoin
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from celery import shared_task

from content.models import RawContent, ContentCluster, ClusterSource
from content.services import find_or_create_cluster, CredibilityScorer
from content.utils import (
    clean_url, extract_full_text_and_image, extract_image_from_raw_data, get_http_session,
)

logger = logging.getLogger(__name__)


def _extract_markdown_image(full_text: str) -> str | None:
    """Extract image URL from markdown-style images in full text."""
    if not full_text or "![" not in full_text:
        return None

    abs_match = re.search(r"!\[.*?\]\((https?://[^\s)]+(?:\?[^\s)]*)?)\)", full_text)
    if abs_match:
        return re.sub(r"\?.*$", "", abs_match.group(1)).strip() or None

    rel_match = re.search(r"!\[.*?\]\((/[^)\s]+(?:\?[^)\s]*)?)\)", full_text)
    if rel_match:
        candidate = urljoin("https://www.aljazeera.com", rel_match.group(1))
        return re.sub(r"\?.*$", "", candidate).strip() or None

    return None


@shared_task(name='content.tasks.process_raw_content', bind=True, max_retries=3, default_retry_delay=60)
def process_raw_content(self, raw_id: int):
    try:
        raw = RawContent.objects.get(id=raw_id)
    except ObjectDoesNotExist:
        logger.warning(f"RawContent {raw_id} not found")
        return

    if raw.processed:
        return

    image_updated = False

    # STEP 1: Extract best possible image
    if not raw.image_url:
        if raw.raw_data:
            raw.image_url = extract_image_from_raw_data(raw.raw_data, raw.url)
            if raw.image_url:
                image_updated = True

        if not raw.image_url:
            img = _extract_markdown_image(raw.full_text)
            if img:
                raw.image_url = img
                image_updated = True

    # STEP 2: Clean URL
    original_url = raw.url
    raw.url = clean_url(raw.url)

    # STEP 3: Save early to avoid races
    update_fields = ["url", "processed"]
    if image_updated or raw.image_url:
        update_fields.append("image_url")
    raw.processed = True
    raw.save(update_fields=update_fields)

    # STEP 4: Clustering
    cluster = find_or_create_cluster(raw.title, raw.snippet, raw.full_text or "")

    # STEP 5: Upgrade cluster image if ours is better
    bad_image_markers = ("?resize=", "?quality=", "placeholder", "no_image", "default")
    if raw.image_url and (
        not cluster.image_url
        or any(bad in (cluster.image_url or "") for bad in bad_image_markers)
    ):
        cluster.image_url = raw.image_url
        cluster.save(update_fields=["image_url"])

    # STEP 6: Upgrade snippet if better
    if raw.snippet and len(raw.snippet) > len(cluster.merged_snippet or ""):
        cluster.merged_snippet = raw.snippet.strip()
        cluster.save(update_fields=["merged_snippet"])

    # STEP 7: Add source to cluster
    display_name = raw.source_name or raw.source_type.replace("_", " ").title()
    if raw.raw_data:
        display_name = (
            raw.raw_data.get("source", {}).get("name")
            or raw.raw_data.get("author_name")
            or raw.raw_data.get("author")
            or display_name
        )

    source_obj, created = ClusterSource.objects.get_or_create(
        cluster=cluster,
        url=raw.url,
        defaults={
            "raw_content": raw,
            "source_name": display_name,
            "credibility_score": CredibilityScorer.score(display_name, raw.source_type),
        },
    )

    # STEP 8: Update cluster metrics
    cluster.source_count = cluster.sources.count()

    if cluster.importance_score == 0.0:
        avg_cred = cluster.sources.aggregate(avg=models.Avg("credibility_score"))["avg"] or 0.5
        cluster.importance_score = min(1.0, avg_cred + 0.2)

    if cluster.source_count >= 5:
        cluster.importance_score = min(1.0, cluster.importance_score + 0.4)
        cluster.trend_score = min(1.0, cluster.trend_score + 0.35)
    elif cluster.source_count >= 3:
        cluster.importance_score = min(1.0, cluster.importance_score + 0.25)
        cluster.trend_score = min(1.0, cluster.trend_score + 0.2)

    cluster.save()

    # STEP 9: Fetch full text only if needed
    if raw.source_type != "gemini" and not raw.full_text:
        fetch_full_text_for_cluster.delay(str(cluster.id))

    logger.info(
        f"{'Created' if cluster.source_count == 1 else 'Merged'} cluster {cluster.id} | "
        f"{raw.title[:60]} | Sources: {cluster.source_count} | Source: {display_name}"
    )


@shared_task(name='content.tasks.fetch_full_text_for_cluster', rate_limit="15/m", bind=True, max_retries=2, default_retry_delay=120)
def fetch_full_text_for_cluster(self, cluster_id):
    try:
        cluster = ContentCluster.objects.get(id=cluster_id)
    except ObjectDoesNotExist:
        logger.warning(f"Cluster {cluster_id} not found")
        return

    # Skip if we already have text
    has_text = RawContent.objects.filter(
        clustersource__cluster=cluster,
    ).exclude(
        models.Q(full_text__isnull=True) | models.Q(full_text=""),
    ).exists()

    if has_text:
        return

    full_text = ""
    best_image = cluster.image_url

    urls_to_try = [clean_url(cluster.canonical_url)]
    urls_to_try.extend(
        clean_url(url)
        for url in cluster.sources.exclude(url=cluster.canonical_url).values_list("url", flat=True)[:5]
    )

    for url in urls_to_try:
        if not url or not url.startswith(("http://", "https://")):
            continue

        text, img = extract_full_text_and_image(url)
        if len(text) > len(full_text):
            full_text = text
            best_image = img or best_image

        if len(full_text) >= 5000:
            break

    if full_text:
        updated = RawContent.objects.filter(
            clustersource__cluster=cluster,
        ).filter(
            models.Q(full_text__isnull=True) | models.Q(full_text=""),
        ).update(full_text=full_text[:30000])

        cluster.full_text_fetched = True
        cluster.image_url = best_image or cluster.image_url
        cluster.save(update_fields=["full_text_fetched", "image_url"])
        logger.info(f"Cluster {cluster_id}: {len(full_text)} chars extracted, {updated} items updated")

        from content.tasks.summaries import generate_ai_summaries
        generate_ai_summaries.delay(str(cluster_id))
    else:
        cluster.full_text_fetched = True
        cluster.save(update_fields=["full_text_fetched"])
        logger.warning(f"Cluster {cluster_id}: no text extracted")
