# content/services.py - Category classification and content clustering

import logging
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from fuzzywuzzy import fuzz

from .constants import CATEGORY_KEYWORDS, SOURCE_TIERS, SOURCE_TYPE_SCORES
from .models import RawContent, ContentCluster, ClusterSource
from .utils import normalize_url, clean_title, extract_key_terms, similarity_ratio, is_video_content

logger = logging.getLogger(__name__)


class CategoryClassifier:
    """Classify content into a single best-fit category using keyword scoring."""

    # Pre-build a flat lookup: keyword → (category, weight)
    # Longer keywords checked first to avoid partial matches
    _keyword_index = None

    @classmethod
    def _build_index(cls):
        if cls._keyword_index is not None:
            return
        cls._keyword_index = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                cls._keyword_index.setdefault(kw.lower(), []).append(category)

    @classmethod
    def classify_content(cls, title: str, snippet: str = "", full_text: str = "") -> list:
        """Return a single-item list with the best category slug."""
        cls._build_index()

        combined_lower = f"{title} {snippet} {full_text}".lower()
        title_lower = title.lower()

        scores = {}
        for keyword, categories in cls._keyword_index.items():
            count = combined_lower.count(keyword)
            if count == 0:
                continue
            title_bonus = title_lower.count(keyword) * 2
            for cat in categories:
                scores[cat] = scores.get(cat, 0) + count + title_bonus

        if scores:
            return [max(scores, key=scores.get)]
        return ["national"]


class CredibilityScorer:
    """Score source credibility based on tiered reputation lists."""

    _flat_lookup = None

    @classmethod
    def _build_lookup(cls):
        if cls._flat_lookup is not None:
            return
        cls._flat_lookup = {}
        for tier_data in SOURCE_TIERS.values():
            for source_name in tier_data["sources"]:
                cls._flat_lookup[source_name] = tier_data["score"]

    @classmethod
    def score(cls, source_name: str, source_type: str = "") -> float:
        cls._build_lookup()

        if not source_name:
            return 0.6

        if source_type == "gemini":
            return 0.90

        source_lower = source_name.lower()
        for key, score in cls._flat_lookup.items():
            if key in source_lower:
                return score

        return SOURCE_TYPE_SCORES.get(source_type, 0.65)


class ContentClusteringService:
    """Find or create content clusters with fuzzy title matching."""

    SIMILARITY_THRESHOLD = 45
    LOOKBACK_DAYS = 5
    CACHE_TIMEOUT = 86400

    @classmethod
    def find_existing_cluster(cls, raw: RawContent) -> ContentCluster | None:
        """Find an existing cluster that matches this raw content."""
        normalized = normalize_url(raw.url)
        cleaned = clean_title(raw.title)

        # 1. Exact URL match via DB index
        if normalized:
            match = ClusterSource.objects.filter(url__iexact=normalized).select_related("cluster").first()
            if match:
                logger.info(f"Exact URL match: {normalized}")
                return match.cluster

        # 2. Cache lookup by title hash (use full hash, not modulo)
        cache_key = f"cluster_title:{hash(cleaned)}"
        cached_id = cache.get(cache_key)
        if cached_id:
            try:
                return ContentCluster.objects.get(id=cached_id)
            except ContentCluster.DoesNotExist:
                cache.delete(cache_key)

        # 3. Fuzzy match against recent clusters (only load titles, not full objects)
        cutoff = timezone.now() - timedelta(days=cls.LOOKBACK_DAYS)
        recent = ContentCluster.objects.filter(
            first_seen_at__gte=cutoff
        ).values_list("id", "canonical_title")

        best_match_id = None
        highest_score = 0

        for cluster_id, cluster_title in recent:
            score = fuzz.token_sort_ratio(cleaned, clean_title(cluster_title))
            if score > highest_score and score >= cls.SIMILARITY_THRESHOLD:
                highest_score = score
                best_match_id = cluster_id

        if best_match_id:
            cluster = ContentCluster.objects.get(id=best_match_id)
            logger.info(f"Fuzzy match {highest_score}%: '{cleaned}' -> '{cluster.canonical_title}'")
            cache.set(cache_key, str(best_match_id), cls.CACHE_TIMEOUT)
            return cluster

        return None

    @classmethod
    def process_raw_content(cls, raw: RawContent):
        """Cluster a RawContent into an existing or new ContentCluster."""
        logger.info(f"Clustering RawContent #{raw.id} - {raw.title[:80]}")
        if raw.processed:
            return

        existing = cls.find_existing_cluster(raw)

        if existing:
            cls._merge_into_cluster(existing, raw)
        else:
            cls._create_new_cluster(raw)

        raw.processed = True
        raw.save(update_fields=["processed"])

    @classmethod
    def _merge_into_cluster(cls, cluster: ContentCluster, raw: RawContent):
        ClusterSource.objects.create(
            cluster=cluster,
            raw_content=raw,
            url=normalize_url(raw.url) or raw.url,
            source_name=raw.source_name or raw.source_type,
            credibility_score=CredibilityScorer.score(raw.source_name, raw.source_type),
        )

        cluster.source_count_increased = True
        cluster.source_count = cluster.sources.count()
        cluster.last_updated_at = timezone.now()

        if len(raw.title) > len(cluster.canonical_title):
            cluster.canonical_title = raw.title

        if not cluster.image_url and raw.image_url:
            cluster.image_url = raw.image_url

        if len(raw.full_text or "") > 1000:
            cluster.content_type = "ARTICLE"

        if not cluster.categories:
            detected = CategoryClassifier.classify_content(
                title=cluster.canonical_title,
                snippet=cluster.merged_snippet or "",
                full_text=raw.full_text or "",
            )
            if detected:
                cluster.categories = detected

        # Regenerate summaries if new content is richer
        needs_resummarize = (
            (raw.full_text and len(raw.full_text) > 500)
            or (raw.snippet and len(raw.snippet) > len(cluster.merged_snippet or ""))
        )
        if needs_resummarize:
            cluster.summary_generated = False
            from content.tasks.summaries import generate_ai_summaries
            generate_ai_summaries.delay(str(cluster.id))

        cluster.save()
        logger.info(f"Merged into cluster {cluster.id} - now {cluster.source_count} sources")

    @classmethod
    def _create_new_cluster(cls, raw: RawContent):
        content_type = "ARTICLE" if len(raw.full_text or "") > 1000 else "NEWS"
        detected = CategoryClassifier.classify_content(
            title=raw.title, snippet=raw.snippet or "", full_text=raw.full_text or "",
        )

        new_cluster = ContentCluster.objects.create(
            canonical_title=raw.title,
            canonical_url=normalize_url(raw.url) or raw.url,
            merged_snippet=raw.snippet or (raw.full_text[:500] if raw.full_text else ""),
            image_url=raw.image_url,
            source_count=1,
            content_type=content_type,
            categories=detected,
            first_seen_at=raw.published_at or timezone.now(),
        )

        ClusterSource.objects.create(
            cluster=new_cluster,
            raw_content=raw,
            url=normalize_url(raw.url) or raw.url,
            source_name=raw.source_name or raw.source_type,
            credibility_score=CredibilityScorer.score(raw.source_name, raw.source_type),
        )

        from content.tasks.summaries import generate_ai_summaries
        generate_ai_summaries.delay(str(new_cluster.id))

        logger.info(f"Created cluster {new_cluster.id}: {raw.title[:60]} categories={detected}")


def find_or_create_cluster(title: str, snippet: str = "", full_text: str = "") -> ContentCluster:
    """
    Aggressive clustering for multi-source content (used by Gemini fetcher).
    Finds the best matching cluster or creates a new one.
    """
    if is_video_content(title):
        cluster = ContentCluster.objects.create(canonical_title=title)
        cluster.categories = CategoryClassifier.classify_content(title, snippet, full_text)
        cluster.save(update_fields=["categories"])
        return cluster

    key_terms = extract_key_terms(title)
    if len(key_terms) < 2:
        cluster = ContentCluster.objects.create(canonical_title=title)
        cluster.categories = CategoryClassifier.classify_content(title, snippet, full_text)
        cluster.save(update_fields=["categories"])
        return cluster

    cutoff = timezone.now() - timedelta(hours=168)
    # Only load id + title for comparison, not full objects
    candidates = (
        ContentCluster.objects.filter(first_seen_at__gte=cutoff)
        .order_by("-first_seen_at")
        .values_list("id", "canonical_title")[:500]
    )

    best_match_id = None
    best_score = 0.0

    for cluster_id, cluster_title in candidates:
        sim = similarity_ratio(title, cluster_title)
        cluster_terms = extract_key_terms(cluster_title)

        overlap = len(key_terms & cluster_terms)
        total_unique = len(key_terms | cluster_terms)
        overlap_score = overlap / max(total_unique, 1)

        combined = (sim * 0.5) + (overlap_score * 0.5)

        if combined > best_score:
            best_score = combined
            best_match_id = cluster_id

        # Immediate merge conditions
        if sim > 0.50:
            return ContentCluster.objects.get(id=cluster_id)
        if overlap >= 4 and sim > 0.35:
            return ContentCluster.objects.get(id=cluster_id)
        if overlap >= 3 and sim > 0.35:
            return ContentCluster.objects.get(id=cluster_id)
        if overlap >= 2 and overlap_score > 0.35:
            return ContentCluster.objects.get(id=cluster_id)
        if overlap >= 1 and sim > 0.40:
            return ContentCluster.objects.get(id=cluster_id)

    if best_match_id and best_score > 0.15:
        return ContentCluster.objects.get(id=best_match_id)

    cluster = ContentCluster.objects.create(canonical_title=title)
    cluster.categories = CategoryClassifier.classify_content(title, snippet, full_text)
    cluster.save(update_fields=["categories"])
    return cluster
