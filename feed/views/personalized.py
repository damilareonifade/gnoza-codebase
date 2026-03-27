import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from content.models import ContentCluster
from feed.serializers import ContentClusterSerializer

logger = logging.getLogger(__name__)


class FeedPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class PersonalizedFeedView(APIView):
    """
    GET /api/v1/feed/feed
    Returns a personalized feed of clusters scored against user preferences.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ContentClusterSerializer
    pagination_class = FeedPagination

    def get(self, request):
        user = request.user

        preferred_topics: list[str] = []
        preferred_locations: list[str] = []

        try:
            prefs = user.preferences
            preferred_topics = [t.lower() for t in (prefs.preferred_topics or [])]
            preferred_locations = [l.lower() for l in (prefs.preferred_locations or [])]
        except AttributeError:
            preferred_topics = ["technology", "science"]

        qs = ContentCluster.objects.filter(
            first_seen_at__gte=timezone.now() - timedelta(days=7)
        ).prefetch_related("sources__raw_content").order_by("-first_seen_at")

        scored = []
        for cluster in qs:
            score = 0.0
            title_lower = cluster.canonical_title.lower()
            cats = [c.lower() for c in (cluster.categories or [])]
            kws = [k.lower() for k in (cluster.keywords or [])]

            for topic in preferred_topics:
                if topic in title_lower or topic in cats or topic in kws:
                    score += 2.0

            for loc in preferred_locations:
                if loc in title_lower:
                    score += 1.5

            hours_old = (timezone.now() - cluster.first_seen_at).total_seconds() / 3600
            score += max(0, 1 - (hours_old / 72)) * 0.8
            score += cluster.trend_score * 0.4
            score += min(cluster.source_count / 10, 1.0) * 0.6

            cluster.relevance_score = round(score, 2)
            scored.append(cluster)

        scored.sort(key=lambda c: c.relevance_score, reverse=True)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(scored, request)
        serializer = ContentClusterSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)
