from django.contrib import admin
from .models import Bookmark, Like, Comment, CommentLike


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "cluster", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "cluster__canonical_title")
    raw_id_fields = ("user", "cluster")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "cluster", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "cluster__canonical_title")
    raw_id_fields = ("user", "cluster")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "cluster", "text_preview", "parent", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "text", "cluster__canonical_title")
    raw_id_fields = ("user", "cluster", "parent")

    def text_preview(self, obj):
        return obj.text[:60] + ("..." if len(obj.text) > 60 else "")
    text_preview.short_description = "Text"


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ("user", "comment", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email",)
    raw_id_fields = ("user", "comment")
