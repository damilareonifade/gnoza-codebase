import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models.signals import post_save

from gnoza.models import TimestampedModel


phone_validator = RegexValidator(
    regex=r'^\+?[\d\s\-\(\)]{10,20}$',
    message="Phone number must be valid (e.g., +1234567890)"
)


def validate_preferred_locations(value):
    if not isinstance(value, list):
        raise ValidationError("Preferred locations must be a list.")
    if len(value) > 5:
        raise ValidationError("Maximum 5 locations allowed.")
    if not all(isinstance(loc, str) and len(loc.strip()) >= 2 for loc in value):
        raise ValidationError("Each location must be at least 2 characters.")


LANGUAGE_CHOICES = [
    ('en', 'English'),
    ('fr', 'French'),
    ('es', 'Spanish'),
    ('de', 'German'),
    ('it', 'Italian'),
    ('pt', 'Portuguese'),
    ('ar', 'Arabic'),
    ('zh', 'Chinese'),
    ('ja', 'Japanese'),
    ('ko', 'Korean'),
    ('hi', 'Hindi'),
    ('ru', 'Russian'),
]


class UserPreference(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="preferences",
    )

    # === Public Profile Fields ===
    full_name = models.CharField(max_length=100, blank=True, default="")
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        validators=[phone_validator],
    )
    bio = models.TextField(blank=True, default="")
    website = models.URLField(blank=True, default="")
    profile_picture = models.ImageField(
        upload_to="preferences/profiles/",
        null=True,
        blank=True,
    )

    # === Personalization ===
    preferred_topics = models.JSONField(default=list, blank=True)
    preferred_sources = models.JSONField(default=list, blank=True, null=True)
    preferred_locations = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_preferred_locations],
    )
    preferred_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default="en",
    )
    country = models.CharField(max_length=50, blank=True, default="")

    # === Push Notifications ===
    fcm_token = models.CharField(max_length=500, blank=True, null=True)

    # === Onboarding State ===
    onboarding_completed = models.BooleanField(default=False)
    onboarding_step = models.CharField(max_length=20, default="signup")

    class Meta:
        db_table = "user_preferences"
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"

    def __str__(self):
        return f"Preferences({self.user.email})"

    def get_display_name(self):
        return self.full_name.strip() or self.user.get_full_name() or self.user.email

    def get_initials(self):
        name = self.get_display_name()
        parts = name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif len(name) >= 2:
            return name[:2].upper()
        return "U"


def create_user_preference(sender, instance, created, **kwargs):
    if created:
        UserPreference.objects.get_or_create(user=instance)


post_save.connect(create_user_preference, sender="accounts.User")
