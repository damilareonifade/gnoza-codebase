from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from gnoza.response import Created, BadRequest
from ..models import SmartReminder
from ..serializers import SmartReminderSerializer


class NLPReminderView(APIView):
    """POST /api/v1/reminders/nlp — create a reminder from natural language."""
    permission_classes = [IsAuthenticated]
    serializer_class = SmartReminderSerializer

    def post(self, request):
        text = request.data.get("text", "").strip()
        if not text:
            return BadRequest("text is required.")

        from ai.gemini_client import GeminiClient
        client = GeminiClient()
        parsed = client.parse_reminder_from_text(text)

        remind_at = parsed.get("first_reminder_at")
        if not remind_at:
            return BadRequest("Could not parse a date from the text.")

        reminder = SmartReminder.objects.create(
            user=request.user,
            title=parsed.get("title", text[:100]),
            description=parsed.get("description", ""),
            reminder_type=parsed.get("reminder_type", "custom"),
            recurrence_pattern=parsed.get("recurrence_pattern", "once"),
            first_reminder_at=remind_at,
            next_reminder_at=remind_at,
            metadata=parsed.get("metadata", {"original_text": text}),
        )
        return Created("Reminder created from text", {
            "parsed": parsed,
            "reminder": SmartReminderSerializer(reminder).data,
        })
