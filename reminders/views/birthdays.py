from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from gnoza.response import Ok, Created, BadRequest
from ..models import SmartReminder
from ..serializers import SmartReminderSerializer


class BirthdayImportView(APIView):
    """POST /api/v1/reminders/birthdays/import — bulk import birthday reminders."""
    permission_classes = [IsAuthenticated]
    serializer_class = SmartReminderSerializer

    def post(self, request):
        birthdays = request.data.get("birthdays", [])
        if not isinstance(birthdays, list) or not birthdays:
            return BadRequest("birthdays must be a non-empty list.")

        created = []
        errors = []
        for entry in birthdays:
            name = entry.get("name", "").strip()
            date_str = entry.get("date")
            if not name or not date_str:
                errors.append({"entry": entry, "error": "name and date are required"})
                continue
            try:
                from dateutil.parser import parse as parse_date
                birth_date = parse_date(date_str)
                now = timezone.now()
                # Schedule for next occurrence of that month/day
                next_birthday = birth_date.replace(year=now.year)
                if next_birthday < now:
                    next_birthday = next_birthday.replace(year=now.year + 1)

                reminder = SmartReminder.objects.create(
                    user=request.user,
                    title=f"{name}'s Birthday",
                    reminder_type="personal",
                    recurrence_pattern="yearly",
                    first_reminder_at=next_birthday,
                    next_reminder_at=next_birthday,
                    metadata={"person_name": name, "birth_date": date_str},
                )
                created.append(SmartReminderSerializer(reminder).data)
            except Exception as e:
                errors.append({"entry": entry, "error": str(e)})

        return Created(
            f"{len(created)} birthday reminder(s) imported",
            {"created": created, "errors": errors},
        )


class UpcomingBirthdaysView(APIView):
    """GET /api/v1/reminders/birthdays/upcoming — birthdays in the next 30 days."""
    permission_classes = [IsAuthenticated]
    serializer_class = SmartReminderSerializer

    def get(self, request):
        now = timezone.now()
        upcoming = SmartReminder.objects.filter(
            user=request.user,
            reminder_type="personal",
            status="active",
            next_reminder_at__lte=now + timedelta(days=30),
        ).order_by("next_reminder_at")
        data = SmartReminderSerializer(upcoming, many=True).data
        return Ok("Upcoming birthdays", {"count": len(data), "birthdays": data})
