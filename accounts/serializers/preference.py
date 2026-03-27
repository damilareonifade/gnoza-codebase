import json
from rest_framework import serializers

from gnoza.exceptions import BadRequest
from ..models import UserPreference


VALID_TOPICS = [
    'national', 'international', 'sport', 'lifestyle', 'business', 'health',
    'fashion', 'technology', 'science', 'art', 'politics',
]


class UserPreferenceSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()

    class Meta:
        model = UserPreference
        fields = [
            "id",
            "full_name",
            "phone_number",
            "bio",
            "website",
            "profile_picture",
            "profile_picture_url",
            "preferred_topics",
            "preferred_sources",
            "preferred_locations",
            "preferred_language",
            "country",
            "onboarding_completed",
            "onboarding_step",
            "display_name",
            "initials",
        ]
        read_only_fields = [
            "id",
            "onboarding_completed",
            "onboarding_step",
            "display_name",
            "initials",
            "profile_picture_url",
        ]

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

    def get_display_name(self, obj):
        return obj.get_display_name()

    def get_initials(self, obj):
        return obj.get_initials()


class UserPreferenceUpdateSerializer(serializers.ModelSerializer):
    preferred_topics = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    preferred_locations = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    preferred_sources = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    class Meta:
        model = UserPreference
        fields = [
            "preferred_topics",
            "preferred_sources",
            "preferred_locations",
            "preferred_language",
            "country",
        ]

    def validate_preferred_topics(self, value):
        return [t for t in value if t in VALID_TOPICS]

    def validate_preferred_locations(self, value):
        if len(value) > 5:
            raise BadRequest("Maximum 5 locations allowed.")
        return [loc.strip() for loc in value if loc.strip()]


class OnboardingUpdateSerializer(serializers.Serializer):
    preferred_topics = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    preferred_locations = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    preferred_language = serializers.ChoiceField(
        choices=[c[0] for c in UserPreference._meta.get_field("preferred_language").choices],
        required=False,
    )
    profile_picture = serializers.ImageField(required=False)
    complete = serializers.BooleanField(required=False, default=False)

    def validate_preferred_topics(self, value):
        return [t for t in value if t in VALID_TOPICS]

    def validate_preferred_locations(self, value):
        if len(value) > 5:
            raise BadRequest("Maximum 5 locations allowed.")
        return [loc.strip() for loc in value if loc.strip()]


class EditProfileSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100, required=False)
    phone_number = serializers.CharField(max_length=20, required=False)
    bio = serializers.CharField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    profile_picture = serializers.ImageField(required=False)
    remove_picture = serializers.BooleanField(required=False, default=False)
