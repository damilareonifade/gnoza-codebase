import uuid
from django.db import models
from django.db.models.signals import post_save

from gnoza.models import TimestampedModel
from gnoza.utils import upload_avatar_to


class Profile(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField(blank=True, default="")
    avatar = models.ImageField(upload_to=upload_avatar_to, null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, default="")
    website = models.URLField(blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "profiles"
        ordering = ("-updated_at",)
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self):
        return f"Profile({self.user.email})"


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


post_save.connect(create_user_profile, sender="accounts.User")
