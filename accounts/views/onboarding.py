import json
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from gnoza.response import Ok, BadRequest
from ..models import UserPreference
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import OnboardingUpdateSerializer, EditProfileSerializer, UserPreferenceSerializer


class OnboardingUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = OnboardingUpdateSerializer

    @extend_schema(
        request=OnboardingUpdateSerializer,
        responses={200: OpenApiResponse(description="Onboarding updated successfully")},
    )
    def put(self, request):
        prefs, _ = UserPreference.objects.get_or_create(user=request.user)

        # Normalize array fields sent as JSON strings from form data
        data = request.data.copy()
        for field in ("preferred_topics", "preferred_locations"):
            raw = data.get(field)
            if isinstance(raw, str):
                try:
                    data[field] = json.loads(raw)
                except (ValueError, TypeError):
                    data[field] = [v.strip() for v in raw.split(",") if v.strip()]

        serializer = OnboardingUpdateSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        if "preferred_topics" in validated:
            prefs.preferred_topics = validated["preferred_topics"]
        if "preferred_locations" in validated:
            prefs.preferred_locations = validated["preferred_locations"]
        if "preferred_language" in validated:
            prefs.preferred_language = validated["preferred_language"]
        if "profile_picture" in request.FILES:
            if prefs.profile_picture:
                prefs.profile_picture.delete(save=False)
            prefs.profile_picture = request.FILES["profile_picture"]

        if validated.get("complete") or (
            prefs.preferred_locations
            and prefs.preferred_language
            and prefs.preferred_topics
        ):
            prefs.onboarding_completed = True
            prefs.onboarding_step = "complete"

        prefs.save()

        return Ok(
            "Onboarding updated successfully",
            UserPreferenceSerializer(prefs, context={"request": request}).data,
        )


class EditProfileView(APIView):
    """
    PUT/PATCH /api/v1/auth/profile/edit
    Update user's public profile fields.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(request=EditProfileSerializer, responses=OpenApiResponse(description="Profile updated"))
    def put(self, request):
        return self._update(request)

    @extend_schema(request=EditProfileSerializer, responses=OpenApiResponse(description="Profile updated"))
    def patch(self, request):
        return self._update(request)

    def _update(self, request):
        prefs, _ = UserPreference.objects.get_or_create(user=request.user)
        serializer = EditProfileSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        if "full_name" in validated:
            prefs.full_name = validated["full_name"][:100]
        if "phone_number" in validated:
            prefs.phone_number = validated["phone_number"][:20]
        if "bio" in validated:
            prefs.bio = validated["bio"]
        if "website" in validated:
            prefs.website = validated["website"]

        if "profile_picture" in request.FILES:
            if prefs.profile_picture:
                prefs.profile_picture.delete(save=False)
            prefs.profile_picture = request.FILES["profile_picture"]
        elif validated.get("remove_picture") and prefs.profile_picture:
            prefs.profile_picture.delete(save=False)
            prefs.profile_picture = None

        prefs.save()

        return Ok(
            "Profile updated successfully",
            UserPreferenceSerializer(prefs, context={"request": request}).data,
        )


class UploadProfilePictureView(APIView):
    """
    POST /api/v1/auth/profile/picture
    Upload or replace the user's profile picture.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=None, responses=OpenApiResponse(description="Profile picture uploaded"))
    def post(self, request):
        if "profile_picture" not in request.FILES:
            return BadRequest("No image provided.")

        prefs, _ = UserPreference.objects.get_or_create(user=request.user)
        if prefs.profile_picture:
            prefs.profile_picture.delete(save=False)
        prefs.profile_picture = request.FILES["profile_picture"]
        prefs.save()

        return Ok(
            "Profile picture updated",
            {
                "profile_picture_url": request.build_absolute_uri(
                    prefs.profile_picture.url
                )
            },
        )


class DeleteProfilePictureView(APIView):
    """
    DELETE /api/v1/auth/profile/picture
    Remove the user's profile picture.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiResponse(description="Profile picture removed"))
    def delete(self, request):
        prefs, _ = UserPreference.objects.get_or_create(user=request.user)
        if not prefs.profile_picture:
            return BadRequest("No profile picture to delete.")
        prefs.profile_picture.delete(save=True)
        return Ok("Profile picture removed")
