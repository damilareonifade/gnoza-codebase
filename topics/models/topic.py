import uuid
from django.db import models
from django.core.validators import MinLengthValidator

from gnoza.models import TimestampedModel


class Topic(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(2)],
    )
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    icon = models.ImageField(upload_to="topics/icons/", null=True, blank=True)
    is_popular = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = "topics"
        ordering = ["order", "name"]
        verbose_name = "Topic"
        verbose_name_plural = "Topics"

    def __str__(self):
        return self.name

    @property
    def followers_count(self):
        return self.user_topics.filter(is_saved=True).count()
