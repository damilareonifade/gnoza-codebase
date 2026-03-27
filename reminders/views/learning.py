from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from gnoza.response import Ok, Created, BadRequest, NotFound, NoContent
from ..models import LearningSchedule
from ..serializers import LearningScheduleSerializer


class LearningScheduleListCreateView(APIView):
    """GET/POST /api/v1/reminders/learning."""
    permission_classes = [IsAuthenticated]
    serializer_class = LearningScheduleSerializer

    @extend_schema(operation_id="reminders_learning_list_all")
    def get(self, request):
        schedules = LearningSchedule.objects.filter(user=request.user)
        data = LearningScheduleSerializer(schedules, many=True).data
        return Ok("Learning schedules", {"count": len(data), "schedules": data})

    def post(self, request):
        serializer = LearningScheduleSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            schedule = serializer.save(user=request.user)
            schedule.generate_sessions()
            schedule.save(update_fields=["sessions"])
            return Created("Learning schedule created", LearningScheduleSerializer(schedule).data)


class LearningScheduleDetailView(APIView):
    """GET/PUT/DELETE /api/v1/reminders/learning/<pk>."""
    permission_classes = [IsAuthenticated]
    serializer_class = LearningScheduleSerializer

    def _get(self, pk, user):
        try:
            return LearningSchedule.objects.get(id=pk, user=user)
        except LearningSchedule.DoesNotExist:
            return None

    @extend_schema(operation_id="reminders_learning_get_by_id")
    def get(self, request, pk):
        schedule = self._get(pk, request.user)
        if not schedule:
            return NotFound("Learning schedule not found.")
        return Ok("Learning schedule", LearningScheduleSerializer(schedule).data)

    def put(self, request, pk):
        schedule = self._get(pk, request.user)
        if not schedule:
            return NotFound("Learning schedule not found.")
        serializer = LearningScheduleSerializer(schedule, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Ok("Learning schedule updated", serializer.data)

    def delete(self, request, pk):
        schedule = self._get(pk, request.user)
        if not schedule:
            return NotFound("Learning schedule not found.")
        schedule.delete()
        return NoContent()


class CompleteSessionView(APIView):
    """POST /api/v1/reminders/learning/<pk>/complete-session."""
    permission_classes = [IsAuthenticated]
    serializer_class = LearningScheduleSerializer

    def post(self, request, pk):
        try:
            schedule = LearningSchedule.objects.get(id=pk, user=request.user)
        except LearningSchedule.DoesNotExist:
            return NotFound("Learning schedule not found.")

        session_number = request.data.get("session_number")
        if not session_number:
            return BadRequest("session_number is required.")

        sessions = schedule.sessions
        updated = False
        for s in sessions:
            if s.get("session_number") == int(session_number) and not s["completed"]:
                s["completed"] = True
                s["notes"] = request.data.get("notes", "")
                updated = True
                break

        if not updated:
            return BadRequest("Session not found or already completed.")

        schedule.sessions = sessions
        schedule.completed_sessions = sum(1 for s in sessions if s["completed"])

        if schedule.completed_sessions >= schedule.total_sessions:
            schedule.status = "completed"
            schedule.completed_at = timezone.now()

        schedule.save(update_fields=["sessions", "completed_sessions", "status", "completed_at"])
        return Ok("Session marked complete", LearningScheduleSerializer(schedule).data)
