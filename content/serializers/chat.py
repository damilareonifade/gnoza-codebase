from rest_framework import serializers

from ..models import ContentChat


class ContentChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentChat
        fields = ["id", "user", "content_id", "messages", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]
