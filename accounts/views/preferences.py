from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from gnoza.response import Ok, BadRequest
from ..models import UserPreference
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import UserPreferenceSerializer, UserPreferenceUpdateSerializer


class UserPreferencesView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = UserPreferenceUpdateSerializer

    @extend_schema(responses=OpenApiResponse(description="User preferences"))
    def get(self, request):
        prefs, _ = UserPreference.objects.get_or_create(user=request.user)
        return Ok(
            "User preferences",
            UserPreferenceSerializer(prefs, context={"request": request}).data,
        )

    @extend_schema(responses=OpenApiResponse(description="User preferences"))
    def put(self, request):
        return self._update(request)

    @extend_schema(responses=OpenApiResponse(description="User preferences"))
    def patch(self, request):
        return self._update(request)

    def _update(self, request):
        prefs, _ = UserPreference.objects.get_or_create(user=request.user)
        serializer = UserPreferenceUpdateSerializer(
            prefs, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        updated_prefs = serializer.save()

        # Handle onboarding_completed flag if sent
        if request.data.get("onboarding_completed") is not None:
            updated_prefs.onboarding_completed = bool(
                request.data["onboarding_completed"]
            )
            if updated_prefs.onboarding_completed:
                updated_prefs.onboarding_step = "complete"
            updated_prefs.save(
                update_fields=["onboarding_completed", "onboarding_step"]
            )

        return Ok(
            "Preferences updated successfully",
            UserPreferenceSerializer(updated_prefs, context={"request": request}).data,
        )


class UserProfileDetailView(APIView):
    """
    GET /api/v1/auth/user-profile
    Return the authenticated user's full profile including preferences.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiResponse(description="User profile details"))
    def get(self, request):
        user = request.user
        prefs, _ = UserPreference.objects.get_or_create(user=user)

        avatar_url = None
        if prefs.profile_picture:
            try:
                avatar_url = request.build_absolute_uri(prefs.profile_picture.url)
            except ValueError:
                avatar_url = None

        return Ok(
            "User profile",
            {
                "user_id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_joined": user.date_joined.isoformat(),
                "profile": {
                    "avatar_url": avatar_url,
                    "initials": prefs.get_initials(),
                    "display_name": prefs.get_display_name(),
                    "full_name": prefs.full_name or "",
                    "phone_number": prefs.phone_number or "",
                    "bio": prefs.bio or "",
                    "website": prefs.website or "",
                    "preferred_topics": prefs.preferred_topics or [],
                    "preferred_language": prefs.preferred_language or "en",
                    "preferred_locations": prefs.preferred_locations or [],
                    "preferred_sources": prefs.preferred_sources or [],
                    "country": prefs.country or "",
                    "onboarding_completed": prefs.onboarding_completed,
                    "onboarding_step": prefs.onboarding_step,
                },
            },
        )


class SaveFCMTokenView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"fcm_token": {"type": "string"}}, "required": ["fcm_token"]}},
        responses={200: OpenApiResponse(description="FCM token saved")},
    )
    def post(self, request):
        """POST /api/v1/auth/fcm-token — save a Firebase Cloud Messaging token."""
        token = request.data.get("fcm_token", "").strip()
        if not token:
            raise BadRequest("fcm_token is required.")

        prefs, _ = UserPreference.objects.get_or_create(user=request.user)
        prefs.fcm_token = token
        prefs.save(update_fields=["fcm_token"])

        return Ok("FCM token saved")
