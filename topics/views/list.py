from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta

from gnoza.response import Ok, BadRequest, NotFound
from content.models import ContentCluster
from ..models import Topic, UserTopic
from ..serializers import TopicSerializer


class AllTopicsView(APIView):
    """GET /api/v1/topics — list all topics with is_saved status."""
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializer

    def get(self, request):
        topics = Topic.objects.all()
        data = TopicSerializer(topics, many=True, context={"request": request}).data
        return Ok("Topics", {"count": len(data), "topics": data})


class PopularTopicsView(APIView):
    """GET /api/v1/topics/popular — dynamically derived trending topics."""
    permission_classes = [AllowAny]
    serializer_class = TopicSerializer

    def get(self, request):
        cutoff = timezone.now() - timedelta(hours=48)

        popular = (
            ContentCluster.objects.filter(
                first_seen_at__gte=cutoff, source_count__gte=2
            )
            .values("categories", "keywords")
            .annotate(
                content_count=Count("id"),
                total_views=Sum("views"),
                avg_importance=Avg("importance_score"),
            )
            .order_by("-content_count", "-total_views", "-avg_importance")[:20]
        )

        scores = {}
        for entry in popular:
            for cat in entry["categories"] or []:
                scores[cat] = scores.get(cat, 0) + entry["content_count"]
            for kw in entry["keywords"] or []:
                scores[kw] = scores.get(kw, 0) + entry["content_count"]

        top_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]

        result = []
        for name, count in top_topics:
            cluster = (
                ContentCluster.objects.filter(
                    Q(categories__icontains=[name]) | Q(keywords__icontains=[name]),
                    first_seen_at__gte=cutoff,
                )
                .order_by("-importance_score", "-first_seen_at")
                .first()
            )
            if cluster:
                thumbnail = cluster.image_url
                if not thumbnail:
                    src = cluster.sources.select_related("raw_content").first()
                    if src and src.raw_content:
                        thumbnail = src.raw_content.image_url
                summary = (
                    cluster.short_summary[:150]
                    if cluster.short_summary and len(cluster.short_summary.strip()) > 50
                    else cluster.merged_snippet[:150]
                    if cluster.merged_snippet and len(cluster.merged_snippet.strip()) > 30
                    else f"Trending topic with {count} active stories"
                )
                result.append({
                    "name": name,
                    "title": cluster.canonical_title,
                    "summary": summary,
                    "thumbnail": thumbnail,
                    "content_count": count,
                    "url": cluster.canonical_url,
                })
            else:
                result.append({
                    "name": name,
                    "title": name,
                    "summary": f"Trending topic with {count} active stories in the last 48 hours",
                    "thumbnail": None,
                    "content_count": count,
                    "url": None,
                })

        return Ok("Popular topics", {
            "popular_topics": result,
            "window_hours": 48,
            "total": len(result),
        })


class TopicContentView(APIView):
    """GET /api/v1/topics/<slug>/content — content clusters for a topic."""
    permission_classes = [AllowAny]
    serializer_class = TopicSerializer

    def get(self, request, slug):
        from feed.serializers import ContentClusterSerializer
        from content.views import StandardPagination

        cutoff = timezone.now() - timedelta(days=14)
        clusters = (
            ContentCluster.objects.filter(first_seen_at__gte=cutoff)
            .filter(
                Q(categories__icontains=[slug]) | Q(keywords__icontains=[slug])
            )
            .exclude(sources__raw_content__source_type="youtube")
            .prefetch_related("sources__raw_content")
            .order_by("-first_seen_at", "-importance_score")
        )

        data = ContentClusterSerializer(clusters, many=True, context={"request": request}).data
        paginator = StandardPagination()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)
