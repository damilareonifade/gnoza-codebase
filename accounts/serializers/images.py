from rest_framework import serializers
from gnoza.exceptions import BadRequest
from accounts.models import UserPreference

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_MB = 5


class AvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=True)

    class Meta:
        model = UserPreference
        fields = ("avatar",)

    def validate_avatar(self, value):
        content_type = getattr(value, "content_type", None)
        if content_type and content_type not in ALLOWED_TYPES:
            raise BadRequest("Avatar must be a JPEG, PNG, or WebP image.")
        if value.size > MAX_SIZE_MB * 1024 * 1024:
            raise BadRequest(f"Avatar must be smaller than {MAX_SIZE_MB} MB.")
        return value
