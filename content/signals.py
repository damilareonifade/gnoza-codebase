# content/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ContentCluster, RawContent
from .services import ContentClusteringService

try:
    from notifications.fcm import send_breaking_story_pushes
except ImportError:
    send_breaking_story_pushes = None

try:
    from feed.serializers import ContentClusterSerializer
except ImportError:
    ContentClusterSerializer = None

try:
    from ai.tasks import enrich_cluster_with_ai
except ImportError:
    enrich_cluster_with_ai = None
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=RawContent)
def handle_new_raw_content(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New RawContent: {instance.title}")
        ContentClusteringService.process_raw_content(instance)

# Broadcast when new cluster created or updated with new sources
@receiver(post_save, sender=ContentCluster)
def broadcast_new_story(sender, instance, created, **kwargs):
    if not ContentClusterSerializer:
        return
    if created or getattr(instance, 'source_count_increased', False):
        channel_layer = get_channel_layer()
        serializer = ContentClusterSerializer(instance)
        story_data = serializer.data

        async_to_sync(channel_layer.group_send)(
            "global_feed",
            {
                "type": "new.story",
                "story": story_data
            }
        )
        logger.info(f"Broadcasted new story: {instance.canonical_title}")

@receiver(post_save, sender=ContentCluster)
def on_new_cluster(sender, instance, created, **kwargs):
    if created and send_breaking_story_pushes:
        send_breaking_story_pushes(instance)


@receiver(post_save, sender=ContentCluster)
def on_cluster_created_or_updated(sender, instance, created, **kwargs):
    if created or getattr(instance, 'source_count_increased', False):
        if enrich_cluster_with_ai:
            enrich_cluster_with_ai.delay(instance.id)
        if send_breaking_story_pushes:
            send_breaking_story_pushes(instance)
