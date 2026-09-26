import logging
from datetime import timedelta
from itertools import zip_longest

from django.db.models import Q, Count
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from gnoza.response import BadRequest, ServiceUnavailable

from ..models import ContentCluster, RawContent, CATEGORY_CHOICES
from .pagination import StandardPagination

logger = logging.getLogger(__name__)

NEWS_WINDOW_DAYS = 30
ARTICLES_WINDOW_DAYS = 60
TRENDING_WINDOW_HOURS = 72
MOST_VIEWED_WINDOW_DAYS = 7
TRENDING_TYPES = ("all", "news", "articles")
TRENDING_PER_TYPE = 25
TRENDING_ORDER = ("-importance_score", "-trend_score", "-views", "-source_count", "-first_seen_at")


def _get_user_topics(request):
    user = request.user
    if user.is_authenticated and hasattr(user, "preferences"):
        return [t.lower() for t in (user.preferences.preferred_topics or [])]
    return []


def _topic_q(topics):
    """Match clusters whose categories or keywords contain any of the topics."""
    return Q(categories__has_any_keys=topics) | Q(keywords__has_any_keys=topics)


def _rank_trending(qs, user_topics):
    """Top trending clusters, with ones matching the user's topics first."""
    qs = qs.prefetch_related("sources__raw_content").order_by(*TRENDING_ORDER)
    if not user_topics:
        return list(qs[:TRENDING_PER_TYPE])
    preferred = list(qs.filter(_topic_q(user_topics))[:TRENDING_PER_TYPE])
    remaining = TRENDING_PER_TYPE - len(preferred)
    if remaining > 0:
        preferred += list(qs.exclude(id__in=[c.id for c in preferred])[:remaining])
    return preferred


def _exclude_youtube_reddit(qs):
    ids = ContentCluster.objects.filter(
        sources__raw_content__source_type__in=["youtube", "reddit"]
    ).values_list("id", flat=True)
    return qs.exclude(id__in=ids)


class CategoriesListView(APIView):
    """GET /api/v1/content/categories/ — list all categories with cluster counts."""
    permission_classes = [AllowAny]

    @extend_schema(responses=OpenApiResponse(description="List of content categories with cluster counts"))
    def get(self, request):
        categories = [
            {
                "slug": slug,
                "name": name,
                "count": ContentCluster.objects.filter(
                    categories__contains=[slug]
                ).count(),
            }
            for slug, name in CATEGORY_CHOICES
        ]
        return Response({"categories": categories, "total": len(categories)})


@method_decorator(cache_page(60 * 5), name="dispatch")
@method_decorator(vary_on_headers("Authorization"), name="dispatch")
class TrendingView(APIView):
    """
    GET /api/v1/content/trending?type=all|news|articles&category=<slug>
    Trending news and articles mixed together. Stories matching the user's
    preferred topics rank first in each bucket, but nothing is hidden.
    """
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of trending news and articles"))
    def get(self, request):
        content_type = request.GET.get("type", "all").strip().lower()
        if content_type not in TRENDING_TYPES:
            return BadRequest(f"type must be one of: {', '.join(TRENDING_TYPES)}")

        try:
            user_topics = _get_user_topics(request)
            category_filter = request.GET.get("category")

            qs = ContentCluster.objects.filter(is_event=False).distinct()
            qs = _exclude_youtube_reddit(qs)
            qs = qs.exclude(
                canonical_title__iregex=(
                    r"(official video|music video|ft\.|feat\.|live stream|vlog|trailer|highlights|full match)"
                )
            )
            if category_filter:
                qs = qs.filter(categories__contains=[category_filter])

            # Same rule as the articles tab: long-form or widely covered stories are articles.
            article_q = Q(content_type="ARTICLE") | Q(source_count__gte=3)
            buckets = []
            if content_type in ("all", "news"):
                buckets.append((qs.exclude(article_q), "news"))
            if content_type in ("all", "articles"):
                buckets.append((qs.filter(article_q), "articles"))

            from feed.serializers import ContentClusterSerializer
            serialized = []
            for bucket_qs, label in buckets:
                clusters = _rank_trending(bucket_qs, user_topics)
                serialized.append([
                    d for d in ContentClusterSerializer(
                        clusters, many=True,
                        context={"request": request, "force_content_type": label},
                    ).data
                    if d
                ])

            # Alternate news and articles so both show up at the top of the list.
            data = [item for group in zip_longest(*serialized) for item in group if item]

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data, request)
            return paginator.get_paginated_response(page)
        except Exception as exc:
            logger.error(f"TrendingView error: {exc}", exc_info=True)
            return ServiceUnavailable("Trending content is unavailable right now")


@method_decorator(cache_page(60 * 10), name="dispatch")
@method_decorator(vary_on_headers("Authorization"), name="dispatch")
class AllContentView(APIView):
    """GET /api/v1/content/filtered-content/all/ — all clusters + events + YouTube."""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of all content (clusters, events, YouTube)"))
    def get(self, request):
        from zoneinfo import ZoneInfo
        from datetime import datetime
        from dateutil.parser import isoparse
        from feed.serializers import ContentClusterSerializer, EventSerializer, YouTubeVideoSerializer
        from ..models import Event

        now = timezone.now()
        user = request.user
        user_topics = _get_user_topics(request)
        user_locations, user_country = [], None
        if user.is_authenticated and hasattr(user, "preferences"):
            prefs = user.preferences
            user_locations = [l.lower() for l in (prefs.preferred_locations or [])]
            user_country = (prefs.country or "").lower() or None

        category_filter = request.GET.get("category")
        all_items = []

        # Clusters
        qs = (
            ContentCluster.objects.annotate(sc=Count("sources"))
            .filter(sc__gte=2)
            .distinct()
        )
        if user_topics:
            qs = qs.filter(_topic_q(user_topics))
        if category_filter:
            qs = qs.filter(categories__contains=[category_filter])
        qs = qs.prefetch_related("sources__raw_content").order_by("-first_seen_at")[:100]
        cluster_data = []
        for cluster in qs:
            try:
                d = ContentClusterSerializer(cluster, context={"request": request}).data
                if d:
                    cluster_data.append(d)
            except Exception as e:
                logger.warning(f"Cluster serialization failed {cluster.id}: {e}")
        all_items.extend(cluster_data)

        # Events (next 10 days)
        events_qs = Event.objects.filter(
            start_time__gte=now - timedelta(hours=6),
            start_time__lte=now + timedelta(days=10),
        ).prefetch_related("sources").order_by("start_time")[:30]
        if user_locations:
            events_qs = events_qs.filter(
                Q(location_name__in=user_locations) | Q(venue_name__in=user_locations)
            )
        if user_country:
            events_qs = events_qs.filter(location_name__icontains=user_country)
        all_items.extend(
            EventSerializer(events_qs, many=True, context={"request": request}).data
        )

        # Standalone YouTube
        yt_qs = RawContent.objects.filter(
            source_type="youtube", clustersource__isnull=True
        ).order_by("-published_at")[:30]
        all_items.extend(YouTubeVideoSerializer(yt_qs, many=True).data)

        # Sort by recency
        UTC = ZoneInfo("UTC")
        def _ts(item):
            for key in ("published_at", "first_seen_at", "start_time"):
                raw = item.get(key)
                if raw:
                    try:
                        dt = isoparse(raw)
                        return dt.astimezone(UTC).replace(tzinfo=None)
                    except Exception:
                        pass
            return datetime(2010, 1, 1)

        all_items.sort(key=_ts, reverse=True)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(all_items, request)
        return paginator.get_paginated_response(page)


@method_decorator(cache_page(60 * 5), name="dispatch")
@method_decorator(vary_on_headers("Authorization"), name="dispatch")
class NewsContentView(APIView):
    """GET /api/v1/content/filtered-content/news/ — recent news clusters."""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of news content clusters"))
    def get(self, request):
        try:
            from feed.serializers import ContentClusterSerializer

            now = timezone.now()
            cutoff = now - timedelta(days=NEWS_WINDOW_DAYS)
            user_topics = _get_user_topics(request)
            category_filter = request.GET.get("category")

            qs = ContentCluster.objects.filter(first_seen_at__gte=cutoff).distinct()
            qs = _exclude_youtube_reddit(qs)

            if user_topics:
                qs = qs.filter(_topic_q(user_topics))
            if category_filter:
                qs = qs.filter(categories__contains=[category_filter])

            qs = qs.prefetch_related("sources__raw_content").order_by("-first_seen_at")[:100]
            data = [d for d in ContentClusterSerializer(qs, many=True, context={"request": request}).data if d]

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data, request)
            return paginator.get_paginated_response(page)
        except Exception as exc:
            logger.error(f"NewsContentView error: {exc}", exc_info=True)
            return Response({"error": str(exc)}, status=500)


@method_decorator(cache_page(60 * 10), name="dispatch")
@method_decorator(vary_on_headers("Authorization"), name="dispatch")
class ArticlesContentView(APIView):
    """GET /api/v1/content/filtered-content/articles/ — articles with 3+ sources."""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of article content clusters"))
    def get(self, request):
        try:
            from feed.serializers import ContentClusterSerializer

            now = timezone.now()
            cutoff = now - timedelta(days=ARTICLES_WINDOW_DAYS)
            user_topics = _get_user_topics(request)
            category_filter = request.GET.get("category")

            qs = ContentCluster.objects.filter(
                source_count__gte=3, first_seen_at__gte=cutoff
            ).distinct()
            qs = _exclude_youtube_reddit(qs)

            if user_topics:
                qs = qs.filter(_topic_q(user_topics))
            if category_filter:
                qs = qs.filter(categories__contains=[category_filter])

            qs = qs.prefetch_related("sources__raw_content").order_by("-source_count", "-first_seen_at")[:100]
            data = [
                d for d in ContentClusterSerializer(
                    qs, many=True, context={"request": request, "force_content_type": "articles"}
                ).data
                if d
            ]

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data, request)
            return paginator.get_paginated_response(page)
        except Exception as exc:
            logger.error(f"ArticlesContentView error: {exc}", exc_info=True)
            return Response({"error": str(exc)}, status=500)


class MostViewedView(APIView):
    """GET /api/v1/content/filtered-content/most-viewed/ — most-viewed clusters."""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of most-viewed content clusters"))
    def get(self, request):
        from feed.serializers import ContentClusterSerializer

        now = timezone.now()
        cutoff = now - timedelta(days=MOST_VIEWED_WINDOW_DAYS)

        qs = ContentCluster.objects.filter(
            first_seen_at__gte=cutoff, source_count__gte=2
        ).distinct()
        qs = _exclude_youtube_reddit(qs)
        qs = qs.prefetch_related("sources__raw_content").order_by(
            "-views", "-source_count", "-first_seen_at"
        )[:100]
        data = [d for d in ContentClusterSerializer(qs, many=True, context={"request": request}).data if d]

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)


class ContentBySourceView(APIView):
    """GET /api/v1/content/filtered-content/by-source/?source=<name>"""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of content clusters filtered by source"))
    def get(self, request):
        from feed.serializers import ContentClusterSerializer

        source = request.GET.get("source", "").strip()
        if not source:
            return Response({"error": "source query param required"}, status=400)

        qs = ContentCluster.objects.filter(
            sources__source_name__icontains=source
        ).prefetch_related("sources__raw_content").order_by("-first_seen_at")[:100]
        data = [d for d in ContentClusterSerializer(qs, many=True, context={"request": request}).data if d]

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)


class ContentByCategoryView(APIView):
    """GET /api/v1/content/filtered-content/by-category/?category=<slug>"""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of content clusters filtered by category"))
    def get(self, request):
        from feed.serializers import ContentClusterSerializer

        category = request.GET.get("category", "").strip().lower()
        if not category:
            return Response({"error": "category query param required"}, status=400)

        qs = ContentCluster.objects.filter(
            categories__contains=[category]
        ).prefetch_related("sources__raw_content").order_by("-first_seen_at")[:100]
        data = [d for d in ContentClusterSerializer(qs, many=True, context={"request": request}).data if d]

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)


class SearchContentView(APIView):
    """GET /api/v1/content/filtered-content/search/?q=<query>"""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of content clusters matching search query"))
    def get(self, request):
        from feed.serializers import ContentClusterSerializer

        q = request.GET.get("q", "").strip()
        if not q or len(q) < 2:
            return Response({"error": "q must be at least 2 characters"}, status=400)

        cutoff = timezone.now() - timedelta(days=90)
        qs = ContentCluster.objects.filter(
            first_seen_at__gte=cutoff
        ).filter(
            Q(canonical_title__icontains=q)
            | Q(merged_snippet__icontains=q)
            | Q(keywords__icontains=q)
        ).prefetch_related("sources__raw_content").order_by("-first_seen_at")[:100]

        data = [d for d in ContentClusterSerializer(qs, many=True, context={"request": request}).data if d]
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)


class IncrementClusterViewCount(APIView):
    """POST /api/v1/content/cluster/view/ — increment view counter for a cluster."""
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses=OpenApiResponse(description="Increment view count for a cluster"))
    def post(self, request):
        cluster_id = request.data.get("id") or request.data.get("cluster_id")
        if not cluster_id:
            return Response({"error": "id required"}, status=400)
        updated = ContentCluster.objects.filter(id=cluster_id).update(
            views=ContentCluster.objects.filter(id=cluster_id).values("views").first()["views"] + 1
            if ContentCluster.objects.filter(id=cluster_id).exists()
            else 1
        )
        if not updated:
            return Response({"error": "Cluster not found"}, status=404)
        return Response({"success": True})
