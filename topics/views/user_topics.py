from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from gnoza.response import Ok, Created, BadRequest, NotFound
from ..models import Topic, UserTopic
from ..serializers import TopicSerializer
from ..services import normalize_topic_slugs, refresh_user_preferred_topics, set_explicit_topics


class UserSavedTopicsView(APIView):
    """GET /api/v1/topics/saved — topics the user follows."""
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializer

    def get(self, request):
        topics = Topic.objects.filter(
            user_topics__user=request.user, user_topics__is_saved=True
        ).order_by("order")

        data = TopicSerializer(topics, many=True, context={"request": request}).data
        if not data:
            return Ok("No saved topics", {"saved_topics": [], "count": 0})
        return Ok("Saved topics", {"saved_topics": data, "count": len(data)})


class ToggleSaveTopicView(APIView):
    """POST /api/v1/topics/<pk>/toggle — save or unsave a topic."""
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializer

    def post(self, request, pk):
        try:
            topic = Topic.objects.get(pk=pk)
        except Topic.DoesNotExist:
            return NotFound("Topic not found.")

        user_topic, created = UserTopic.objects.get_or_create(
            user=request.user, topic=topic, defaults={"is_saved": True}
        )
        if not created:
            user_topic.is_saved = not user_topic.is_saved
            user_topic.save(update_fields=["is_saved"])

        preferred_topics = refresh_user_preferred_topics(request.user)
        action = "saved" if user_topic.is_saved else "unsaved"
        return Ok(f"Topic {action}", {
            "topic_id": str(topic.id),
            "name": topic.name,
            "is_saved": user_topic.is_saved,
            "preferred_topics": preferred_topics,
        })


class BulkSaveTopicsView(APIView):
    """POST /api/v1/topics/bulk-save — save multiple topics at once."""
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializer

    def post(self, request):
        topic_ids = request.data.get("topic_ids", [])
        if not isinstance(topic_ids, list) or not topic_ids:
            return BadRequest("topic_ids must be a non-empty list.")

        topics = Topic.objects.filter(id__in=topic_ids)
        if topics.count() != len(topic_ids):
            found_ids = set(str(t.id) for t in topics)
            missing = [tid for tid in topic_ids if str(tid) not in found_ids]
            return BadRequest(f"Some topic IDs not found: {missing}")

        saved = []
        for topic in topics:
            UserTopic.objects.update_or_create(
                user=request.user, topic=topic, defaults={"is_saved": True}
            )
            saved.append({"id": str(topic.id), "name": topic.name})

        preferred_topics = refresh_user_preferred_topics(request.user)
        return Ok(f"{len(saved)} topics saved", {"saved_topics": saved, "preferred_topics": preferred_topics})


class UpdateUserTopicsView(APIView):
    """PUT /api/v1/topics/update — replace the topics the user picked (names or slugs)."""
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializer

    def put(self, request):
        topic_names = request.data.get("topics", [])
        if not isinstance(topic_names, list):
            return BadRequest("topics must be a list of topic names.")

        slugs = normalize_topic_slugs(topic_names)
        invalid = [t for t in topic_names if str(t).strip().lower() not in slugs]
        if invalid:
            all_names = list(Topic.objects.values_list("name", flat=True))
            return BadRequest(f"Invalid topic names: {invalid}. Available: {all_names}")

        preferred_topics = set_explicit_topics(request.user, slugs)
        return Ok("Topics updated", {
            "selected_topics": slugs,
            "preferred_topics": preferred_topics,
            "count": len(preferred_topics),
        })
