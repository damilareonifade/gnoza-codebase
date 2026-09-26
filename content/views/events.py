import logging
from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from gnoza.response import Ok, Created, NoContent, BadRequest, NotFound
from ..models import Event, EventAttendee, ContentCluster, CATEGORY_CHOICES
from .pagination import StandardPagination

logger = logging.getLogger(__name__)


class EventsContentView(APIView):
    """GET /api/v1/content/filtered-content/events/ — upcoming events (next 90 days)."""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of upcoming events"))
    def get(self, request):
        from feed.serializers import EventSerializer

        now = timezone.now()
        user = request.user
        user_locations, user_country = [], None
        if user.is_authenticated and hasattr(user, "preferences"):
            prefs = user.preferences
            user_locations = [l.lower() for l in (prefs.preferred_locations or [])]
            user_country = (prefs.country or "").lower() or None

        qs = Event.objects.filter(
            start_time__gte=now,
            start_time__lte=now + timedelta(days=90),
        )
        if user_locations:
            qs = qs.filter(
                Q(location_name__in=user_locations) | Q(venue_name__in=user_locations)
            )
        if user_country:
            qs = qs.filter(location_name__icontains=user_country)
        qs = qs.order_by("start_time")

        data = EventSerializer(qs, many=True, context={"request": request}).data
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)


class UpcomingEventsView(APIView):
    """GET /api/v1/content/filtered-content/events/upcoming/ — events in next 7 days."""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of events in the next 7 days"))
    def get(self, request):
        from feed.serializers import EventSerializer

        now = timezone.now()
        qs = Event.objects.filter(
            start_time__gte=now,
            start_time__lte=now + timedelta(days=7),
        ).order_by("start_time")
        data = EventSerializer(qs, many=True, context={"request": request}).data
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)


class NearMeEventsView(APIView):
    """GET /api/v1/content/filtered-content/events/near-me/?lat=&lng=&radius= — geo events."""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of nearby events"))
    def get(self, request):
        from feed.serializers import EventSerializer
        from django.db.models import FloatField
        from django.db.models.functions import Cast
        import math

        lat = request.GET.get("lat")
        lng = request.GET.get("lng")
        radius_km = float(request.GET.get("radius", 50))

        now = timezone.now()
        qs = Event.objects.filter(
            start_time__gte=now,
            latitude__isnull=False,
            longitude__isnull=False,
        ).order_by("start_time")[:200]

        if lat and lng:
            try:
                lat = float(lat)
                lng = float(lng)
                nearby = []
                for e in qs:
                    dlat = float(e.latitude) - lat
                    dlng = float(e.longitude) - lng
                    dist = math.sqrt(dlat**2 + dlng**2) * 111
                    if dist <= radius_km:
                        e._distance_km = round(dist, 1)
                        nearby.append(e)
                nearby.sort(key=lambda e: e._distance_km)
                data = EventSerializer(nearby, many=True, context={"request": request}).data
            except (ValueError, TypeError):
                data = EventSerializer(qs, many=True, context={"request": request}).data
        else:
            data = EventSerializer(qs, many=True, context={"request": request}).data

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)


class EventsByLocationView(APIView):
    """GET /api/v1/content/filtered-content/events/by-location/<location>/"""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of events by location"))
    def get(self, request, location):
        from feed.serializers import EventSerializer

        now = timezone.now()
        qs = Event.objects.filter(
            start_time__gte=now,
            location_name__icontains=location,
        ).order_by("start_time")

        data = EventSerializer(qs, many=True, context={"request": request}).data
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)


class EventDetailView(APIView):
    """GET /api/v1/content/events/<pk>/ — single event detail."""
    permission_classes = [AllowAny]

    @extend_schema(responses=OpenApiResponse(description="Single event detail"))
    def get(self, request, pk):
        from feed.serializers import EventSerializer

        event = get_object_or_404(Event, pk=pk)
        return Ok("Event detail", EventSerializer(event, context={"request": request}).data)


class JoinEventView(APIView):
    """POST /api/v1/content/events/<pk>/join/ — RSVP to an event."""
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=OpenApiResponse(description="Join an event"))
    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        _, created = EventAttendee.objects.get_or_create(
            event=event, user=request.user
        )
        if created:
            return Created("Joined event", {"event_id": str(event.id), "attendee_count": event.attendee_count})
        return Ok("Already joined", {"event_id": str(event.id), "attendee_count": event.attendee_count})


class LeaveEventView(APIView):
    """POST /api/v1/content/events/<pk>/leave/ — cancel RSVP."""
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=OpenApiResponse(description="Leave an event"))
    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        deleted, _ = EventAttendee.objects.filter(
            event=event, user=request.user
        ).delete()
        if deleted:
            return Ok("Left event", {"event_id": str(event.id), "attendee_count": event.attendee_count})
        return BadRequest("You are not attending this event.")


class EventCategoriesView(APIView):
    """GET /api/v1/content/events/categories/ — list event category options."""
    permission_classes = [AllowAny]

    @extend_schema(responses=OpenApiResponse(description="List of event categories"))
    def get(self, request):
        return Ok("Event categories", {"categories": [c[0] for c in CATEGORY_CHOICES]})


class YouTubeRecommendationsView(APIView):
    """GET /api/v1/content/youtube/recommendations/ — YouTube videos."""
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    @extend_schema(responses=OpenApiResponse(description="Paginated list of YouTube video recommendations"))
    def get(self, request):
        from feed.serializers import YouTubeVideoSerializer
        from ..models import RawContent
        from django.db.models import Q

        user = request.user
        user_topics, user_locations, user_country = [], [], None
        if user.is_authenticated and hasattr(user, "preferences"):
            prefs = user.preferences
            user_topics = [t.lower() for t in (prefs.preferred_topics or [])]
            user_locations = [l.lower() for l in (prefs.preferred_locations or [])]
            user_country = (prefs.country or "").lower() or None

        qs = RawContent.objects.filter(source_type="youtube")
        q = Q()
        if user_topics:
            q |= Q(raw_data__categories__has_any_keys=user_topics) | Q(raw_data__keywords__has_any_keys=user_topics)
        if user_country:
            q |= Q(raw_data__user_country=user_country)
        if q:
            qs = qs.filter(q)
        qs = qs.order_by("-published_at")[:100]

        data = [d for d in YouTubeVideoSerializer(qs, many=True).data if d]
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)
