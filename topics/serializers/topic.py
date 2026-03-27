from rest_framework import serializers
from ..models import Topic, UserTopic


class TopicSerializer(serializers.ModelSerializer):
    followers_count = serializers.IntegerField(read_only=True)
    is_saved = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            "id", "name", "slug", "description",
            "icon", "is_popular", "order",
            "followers_count", "is_saved", "created_at",
        ]
        read_only_fields = ["id", "created_at", "followers_count"]

    def get_is_saved(self, obj) -> bool:
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return UserTopic.objects.filter(
                user=request.user, topic=obj, is_saved=True
            ).exists()
        return False


class UserTopicSerializer(serializers.ModelSerializer):
    topic = TopicSerializer(read_only=True)

    class Meta:
        model = UserTopic
        fields = ["id", "topic", "is_saved", "saved_at", "updated_at"]
        read_only_fields = ["id", "saved_at", "updated_at"]
