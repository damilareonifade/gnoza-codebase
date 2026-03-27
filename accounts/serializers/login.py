from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from gnoza.exceptions import AuthenticationFailed, InactiveAccountException
from accounts.models import User


class UserMiniSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "is_active")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True)
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    user = UserMiniSerializer(read_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower()
        password = attrs["password"]

        user = authenticate(request=self.context.get("request"), username=email, password=password)

        if user is None:
            raise AuthenticationFailed("Invalid email or password.")

        if not user.is_active:
            raise InactiveAccountException("Account is inactive. Please verify your email.")

        refresh = RefreshToken.for_user(user)
        attrs["access_token"] = str(refresh.access_token)
        attrs["refresh_token"] = str(refresh)
        attrs["user"] = user
        return attrs
