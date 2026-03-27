import uuid
import hashlib
import secrets
from datetime import timedelta
from django.db import models
from django.utils import timezone

from gnoza.models import TimestampedModel


class TokenPurpose(models.TextChoices):
    ACCOUNT_ACTIVATION = "account_activation", "Account Activation"
    PASSWORD_RESET = "password_reset", "Password Reset"


class UserToken(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    purpose = models.CharField(
        max_length=30,
        choices=TokenPurpose.choices,
        default=TokenPurpose.ACCOUNT_ACTIVATION,
    )
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = "user_tokens"
        ordering = ("-created_at",)
        verbose_name = "User Token"
        verbose_name_plural = "User Tokens"

    def __str__(self):
        return f"{self.purpose} token for {self.user.email}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.used and not self.is_expired

    @classmethod
    def create_for_user(cls, user, purpose: str, hours: int = 24) -> tuple["UserToken", str]:
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        cls.objects.filter(user=user, purpose=purpose, used=False).delete()
        instance = cls.objects.create(
            user=user,
            token_hash=token_hash,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(hours=hours),
        )
        return instance, raw_token

    @classmethod
    def verify(cls, raw_token: str, purpose: str) -> "UserToken | None":
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        try:
            token = cls.objects.select_related("user").get(
                token_hash=token_hash, purpose=purpose
            )
        except cls.DoesNotExist:
            return None
        if not token.is_valid:
            return None
        return token
