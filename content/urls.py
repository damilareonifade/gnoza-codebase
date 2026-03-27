from django.urls import path
from .views import *

urlpatterns = [
    # AI Chat
    path("chat/<uuid:content_id>/narrate", NarrateAIResponseView.as_view(), name="chat-narrate"),
    path("chat/<uuid:content_id>", ContentChatView.as_view(), name="content-chat"),

    # Trending
    path("trending", TrendingView.as_view(), name="trending"),

    # Filtered content
    path("filtered-content/all", AllContentView.as_view(), name="all-content"),
    path("filtered-content/news", NewsContentView.as_view(), name="news-content"),
    path("filtered-content/articles", ArticlesContentView.as_view(), name="articles-content"),
    path("filtered-content/most-viewed", MostViewedView.as_view(), name="most-viewed"),
    path("filtered-content/by-source", ContentBySourceView.as_view(), name="by-source"),
    path("filtered-content/by-category", ContentByCategoryView.as_view(), name="by-category"),
    path("filtered-content/search", SearchContentView.as_view(), name="search"),

    # Events — specific paths before parameterised ones
    path("filtered-content/events/upcoming", UpcomingEventsView.as_view(), name="upcoming-events"),
    path("filtered-content/events/near-me", NearMeEventsView.as_view(), name="near-me-events"),
    path("filtered-content/events/by-location/<str:location>", EventsByLocationView.as_view(), name="events-by-location"),
    path("filtered-content/events", EventsContentView.as_view(), name="events"),
    path("events/categories", EventCategoriesView.as_view(), name="event-categories"),
    path("events/<uuid:pk>/join", JoinEventView.as_view(), name="join-event"),
    path("events/<uuid:pk>/leave", LeaveEventView.as_view(), name="leave-event"),
    path("events/<uuid:pk>", EventDetailView.as_view(), name="event-detail"),

    # YouTube
    path("youtube/recommendations", YouTubeRecommendationsView.as_view(), name="youtube-recommendations"),

    # Metadata
    path("categories", CategoriesListView.as_view(), name="categories"),
    path("cluster/view", IncrementClusterViewCount.as_view(), name="cluster-view"),

    # AI analysis
    path("deep-dive/<uuid:content_id>", DeepDiveView.as_view(), name="deep-dive"),
    path("ask-gnoza/<uuid:content_id>", AskGnozaView.as_view(), name="ask-gnoza"),
]
