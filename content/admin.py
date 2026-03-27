from django.contrib import admin
from .models import RawContent, ContentCluster, ClusterSource, Event, EventSource, EventAttendee, ContentChat


@admin.register(ContentCluster)
class ContentClusterAdmin(admin.ModelAdmin):
    list_display = ("canonical_title", "content_type", "source_count", "views", "trend_score", "first_seen_at")
    list_filter = ("content_type", "is_event", "summary_generated")
    search_fields = ("canonical_title", "merged_snippet")
    readonly_fields = ("first_seen_at", "last_updated_at")


@admin.register(RawContent)
class RawContentAdmin(admin.ModelAdmin):
    list_display = ("title", "source_type", "source_name", "processed", "fetched_at")
    list_filter = ("source_type", "processed")
    search_fields = ("title", "source_name")


@admin.register(ClusterSource)
class ClusterSourceAdmin(admin.ModelAdmin):
    list_display = ("source_name", "cluster", "credibility_score", "added_at")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("canonical_title", "location_name", "start_time", "source_count")
    list_filter = ("categories",)
    search_fields = ("canonical_title", "location_name")


admin.site.register(EventSource)
admin.site.register(EventAttendee)
admin.site.register(ContentChat)
