from rest_framework import serializers
from accounts.models import Profile, User


class UserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "date_joined")
        read_only_fields = ("id", "email", "date_joined")


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "id",
            "user",
            "bio",
            "avatar",
            "avatar_url",
            "location",
            "website",
            "date_of_birth",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "avatar_url", "created_at", "updated_at")
        extra_kwargs = {"avatar": {"write_only": True}}

    def get_avatar_url(self, obj) -> str | None:
        request = self.context.get("request")
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        for attr, value in user_data.items():
            if attr not in ("email",):
                setattr(user, attr, value)
        user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
