from typing import Optional

from django.utils.timesince import timesince
from django.utils import timezone
from rest_framework import serializers

from ..models import Comment, CommentLike


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id", "user_id", "username", "avatar_url",
            "text", "created_at", "updated_at",
            "time_ago", "like_count", "is_liked", "replies",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at",
            "time_ago", "like_count", "is_liked", "replies",
        ]

    def get_user_id(self, obj) -> str:
        return str(obj.user.id)

    def get_username(self, obj) -> str:
        return obj.user.email

    def get_avatar_url(self, obj) -> Optional[str]:
        if hasattr(obj.user, "preferences") and obj.user.preferences.profile_picture:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.user.preferences.profile_picture.url)
            return obj.user.preferences.profile_picture.url
        return None

    def get_time_ago(self, obj) -> str:
        return timesince(obj.created_at, now=timezone.now()) + " ago"

    def get_like_count(self, obj) -> int:
        return obj.comment_likes.count()

    def get_is_liked(self, obj) -> bool:
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return CommentLike.objects.filter(user=request.user, comment=obj).exists()
        return False

    def get_replies(self, obj) -> list:
        if hasattr(obj, "replies") and obj.replies.exists():
            return CommentSerializer(
                obj.replies.all().order_by("created_at"),
                many=True,
                context=self.context,
            ).data
        return []
