from rest_framework import serializers
from gnoza.exceptions import BadRequest
from accounts.models import User


class RegisterSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True, min_length=3, max_length=150)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "username", "password", "first_name", "last_name", "is_active")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise BadRequest("A user with this email already exists.")
        return value.lower()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise BadRequest("A user with this username already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        instance = User(**validated_data)
        instance.set_password(password)
        instance.save()
        return instance
