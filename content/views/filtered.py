import logging
from datetime import timedelta

from django.db.models import Q, Count
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from ..models import ContentCluster, RawContent, CATEGORY_CHOICES
from .pagination import StandardPagination

logger = logging.getLogger(__name__)

NEWS_WINDOW_DAYS = 30
ARTICLES_WINDOW_DAYS = 60
TRENDING_WINDOW_HOURS = 72
MOST_VIEWED_WINDOW_DAYS = 7


def _get_user_topics(request):
    user = request.user
    if user.is_authenticated and hasattr(user, "preferences"):
        return [t.lower() for t in (user.preferences.preferred_topics or [])]
    return []


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
class TrendingView(APIView):
    """GET /api/v1/content/trending/ — trending clusters within 72 hours."""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of trending content clusters"))
    def get(self, request):
        try:
            user_topics = _get_user_topics(request)
            category_filter = request.GET.get("category")

            qs = ContentCluster.objects.all().distinct()
            qs = _exclude_youtube_reddit(qs)
            qs = qs.exclude(
                canonical_title__iregex=(
                    r"(official video|music video|ft\.|feat\.|live stream|vlog|trailer|highlights|full match)"
                )
            )

            if user_topics:
                qs = qs.filter(
                    Q(categories__overlap=user_topics)
                    | Q(keywords__overlap=user_topics)
                )
            if category_filter:
                qs = qs.filter(categories__contains=[category_filter])

            qs = qs.prefetch_related("sources__raw_content").order_by(
                "-importance_score", "-views", "-source_count", "-first_seen_at"
            )[:50]

            from feed.serializers import ContentClusterSerializer
            data = [d for d in ContentClusterSerializer(qs, many=True, context={"request": request}).data if d]

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data, request)
            return paginator.get_paginated_response(page)
        except Exception as exc:
            logger.error(f"TrendingView error: {exc}", exc_info=True)
            return Response({"error": str(exc), "results": []}, status=500)


@method_decorator(cache_page(60 * 10), name="dispatch")
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
            qs = qs.filter(
                Q(categories__overlap=user_topics) | Q(keywords__overlap=user_topics)
            )
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
                qs = qs.filter(
                    Q(categories__overlap=user_topics)
                    | Q(keywords__overlap=user_topics)
                )
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
                qs = qs.filter(
                    Q(categories__overlap=user_topics)
                    | Q(keywords__overlap=user_topics)
                )
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
