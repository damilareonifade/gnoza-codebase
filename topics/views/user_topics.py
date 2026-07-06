from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from gnoza.response import Ok, Created, BadRequest, NotFound
from ..models import Topic, UserTopic
from ..serializers import TopicSerializer


class UserSavedTopicsView(APIView):
    """GET /api/v1/topics/saved — topics the user follows."""
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializer

    def get(self, request):
        prefs = getattr(request.user, "preferences", None)
        topic_names = prefs.preferred_topics if prefs else []

        if not topic_names:
            return Ok("No saved topics", {"saved_topics": [], "count": 0})

        topics = Topic.objects.filter(name__in=topic_names).order_by("order")
        data = TopicSerializer(topics, many=True, context={"request": request}).data
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

        action = "saved" if user_topic.is_saved else "unsaved"
        return Ok(f"Topic {action}", {"topic_id": str(topic.id), "name": topic.name, "is_saved": user_topic.is_saved})


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

        return Ok(f"{len(saved)} topics saved", {"saved_topics": saved})


class UpdateUserTopicsView(APIView):
    """PUT /api/v1/topics/update — replace the user's preferred_topics list."""
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializer

    def put(self, request):
        topic_names = request.data.get("topics", [])
        if not isinstance(topic_names, list):
            return BadRequest("topics must be a list of topic names.")

        if topic_names:
            existing = set(Topic.objects.filter(name__in=topic_names).values_list("name", flat=True))
            invalid = [t for t in topic_names if t not in existing]
            if invalid:
                all_names = list(Topic.objects.values_list("name", flat=True))
                return BadRequest(f"Invalid topic names: {invalid}. Available: {all_names}")

        prefs = getattr(request.user, "preferences", None)
        if not prefs:
            from accounts.models import UserPreference
            prefs = UserPreference.objects.create(user=request.user)

        prefs.preferred_topics = topic_names
        prefs.save(update_fields=["preferred_topics"])

        return Ok("Topics updated", {"preferred_topics": topic_names, "count": len(topic_names)})
