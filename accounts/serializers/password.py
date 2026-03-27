from rest_framework import serializers
from gnoza.exceptions import BadRequest, NotFound, AuthenticationFailed
from accounts.models import User, UserToken, TokenPurpose


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise AuthenticationFailed("Current password is incorrect.")
        if attrs["new_password"] != attrs["confirm_password"]:
            raise BadRequest("New passwords do not match.")
        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class PasswordForgotSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not User.objects.filter(email__iexact=value, is_active=True).exists():
            raise NotFound("No active account found with this email address.")
        return value.lower()

    def save(self) -> tuple[User, str]:
        user = User.objects.get(email=self.validated_data["email"])
        _, raw_token = UserToken.create_for_user(
            user, purpose=TokenPurpose.PASSWORD_RESET, hours=1
        )
        return user, raw_token


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise BadRequest("Passwords do not match.")
        token_obj = UserToken.verify(attrs["token"], purpose=TokenPurpose.PASSWORD_RESET)
        if token_obj is None:
            raise BadRequest("Invalid or expired reset token.")
        attrs["token_obj"] = token_obj
        return attrs

    def save(self):
        token_obj = self.validated_data["token_obj"]
        user = token_obj.user
        user.set_password(self.validated_data["new_password"])
        user.save()
        token_obj.used = True
        token_obj.save(update_fields=["used"])
        return user
