from django.contrib import admin
from .models import Topic, UserTopic


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_popular", "order", "followers_count", "created_at")
    list_filter = ("is_popular",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


@admin.register(UserTopic)
class UserTopicAdmin(admin.ModelAdmin):
    list_display = ("user", "topic", "is_saved", "saved_at")
    list_filter = ("is_saved",)
    search_fields = ("user__email", "topic__name")
    raw_id_fields = ("user",)
