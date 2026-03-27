from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from gnoza.response import Ok, Created, BadRequest, NotFound, NoContent
from ..models import SmartReminder
from ..serializers import SmartReminderSerializer


class ReminderListCreateView(APIView):
    """GET/POST /api/v1/reminders — list or create reminders."""
    permission_classes = [IsAuthenticated]
    serializer_class = SmartReminderSerializer

    @extend_schema(operation_id="reminders_list_all")
    def get(self, request):
        status_filter = request.query_params.get("status")
        qs = SmartReminder.objects.filter(user=request.user)
        if status_filter:
            qs = qs.filter(status=status_filter)
        data = SmartReminderSerializer(qs, many=True).data
        return Ok("Reminders", {"count": len(data), "reminders": data})

    @extend_schema(operation_id="reminders_create_new")
    def post(self, request):
        serializer = SmartReminderSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(user=request.user)
            return Created("Reminder created", serializer.data)


class ReminderDetailView(APIView):
    """GET/PUT/DELETE /api/v1/reminders/<pk>."""
    permission_classes = [IsAuthenticated]
    serializer_class = SmartReminderSerializer

    def _get_reminder(self, pk, user):
        try:
            return SmartReminder.objects.get(id=pk, user=user)
        except SmartReminder.DoesNotExist:
            return None

    @extend_schema(operation_id="reminders_get_by_id")
    def get(self, request, pk):
        reminder = self._get_reminder(pk, request.user)
        if not reminder:
            return NotFound("Reminder not found.")
        return Ok("Reminder", SmartReminderSerializer(reminder).data)

    def put(self, request, pk):
        reminder = self._get_reminder(pk, request.user)
        if not reminder:
            return NotFound("Reminder not found.")
        serializer = SmartReminderSerializer(reminder, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Ok("Reminder updated", serializer.data)

    def delete(self, request, pk):
        reminder = self._get_reminder(pk, request.user)
        if not reminder:
            return NotFound("Reminder not found.")
        reminder.delete()
        return NoContent()


class QuickReminderView(APIView):
    """POST /api/v1/reminders/quick — create a simple one-time reminder."""
    permission_classes = [IsAuthenticated]
    serializer_class = SmartReminderSerializer

    def post(self, request):
        title = request.data.get("title", "").strip()
        remind_at = request.data.get("remind_at")
        description = request.data.get("description", "")

        if not title:
            return BadRequest("title is required.")
        if not remind_at:
            return BadRequest("remind_at is required.")

        reminder = SmartReminder.objects.create(
            user=request.user,
            title=title,
            description=description,
            reminder_type="custom",
            recurrence_pattern="once",
            first_reminder_at=remind_at,
            next_reminder_at=remind_at,
        )
        return Created("Reminder set", SmartReminderSerializer(reminder).data)


class ReminderPauseResumeView(APIView):
    """POST /api/v1/reminders/<pk>/pause and /resume."""
    permission_classes = [IsAuthenticated]
    serializer_class = SmartReminderSerializer

    @extend_schema(operation_id="reminders_pause_resume")
    def post(self, request, pk, action):
        try:
            reminder = SmartReminder.objects.get(id=pk, user=request.user)
        except SmartReminder.DoesNotExist:
            return NotFound("Reminder not found.")

        if action == "pause":
            reminder.status = "paused"
        elif action == "resume":
            reminder.status = "active"
        else:
            return BadRequest("Invalid action.")
        reminder.save(update_fields=["status"])
        return Ok(f"Reminder {action}d", SmartReminderSerializer(reminder).data)
