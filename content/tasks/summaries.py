# content/tasks/summaries.py - AI-powered summary generation tasks

import re
import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from celery import shared_task
import google.generativeai as genai

from content.models import RawContent, ContentCluster, Event

logger = logging.getLogger(__name__)

# Lazy Gemini model initialization
_gemini_model = None


def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-2.5-pro")
    return _gemini_model


# Minimum length requirements
MIN_SHORT = 120
MIN_MEDIUM = 300
MIN_LONG = 1200


def _build_fallback_summaries(cluster: ContentCluster, full_text: str = ""):
    """Build fallback summaries from snippet/title when AI is unavailable."""
    base = cluster.canonical_title
    if cluster.merged_snippet:
        base = f"{cluster.canonical_title}. {cluster.merged_snippet}"

    cluster.short_summary = base[:250] if len(base) >= MIN_SHORT else f"{base}."[:250]
    cluster.medium_summary = base[:600] if len(base) >= MIN_MEDIUM else f"{base}. Follow this story for more updates."[:600]

    if full_text and len(full_text) > 200:
        cluster.long_summary = f"{base}. {full_text[:6000]}"[:8000]
    elif cluster.merged_snippet:
        cluster.long_summary = (
            f"{base}. This story is developing with ongoing coverage. "
            "More details and analysis will be provided as information becomes available."
        )[:1500]
    else:
        cluster.long_summary = (
            f"{base}. This is a developing news story. "
            "Our team is gathering more information from reliable sources."
        )[:1500]


def _parse_ai_summaries(text: str, cluster: ContentCluster):
    """Parse SHORT/MEDIUM/LONG from Gemini response text."""
    short_match = re.search(r"SHORT:\s*(.+?)(?=MEDIUM:|$)", text, re.DOTALL)
    medium_match = re.search(r"MEDIUM:\s*(.+?)(?=LONG:|$)", text, re.DOTALL)
    long_match = re.search(r"LONG:\s*(.+?)$", text, re.DOTALL)

    if short_match:
        short_text = short_match.group(1).strip()
        if len(short_text) >= MIN_SHORT:
            cluster.short_summary = short_text
        else:
            cluster.short_summary = f"{short_text} {cluster.merged_snippet or ''}"[:200].strip()

    if medium_match:
        medium_text = medium_match.group(1).strip()
        if len(medium_text) >= MIN_MEDIUM:
            cluster.medium_summary = medium_text
        else:
            cluster.medium_summary = f"{medium_text} {cluster.merged_snippet or ''}"[:500].strip()

    if long_match:
        long_text = long_match.group(1).strip()
        if len(long_text) >= MIN_LONG:
            cluster.long_summary = long_text[:8000]
        else:
            cluster.long_summary = long_text[:8000]


@shared_task(name='content.tasks.generate_ai_summaries', bind=True, max_retries=2, default_retry_delay=30)
def generate_ai_summaries(self, cluster_id):
    """Generate rich AI-powered summaries using Gemini."""
    try:
        cluster = ContentCluster.objects.get(id=cluster_id)
        if cluster.summary_generated:
            return

        # Get the longest full text from any source
        full_text = ""
        for raw in RawContent.objects.filter(clustersource__cluster=cluster).only("full_text"):
            if raw.full_text and len(raw.full_text) > len(full_text):
                full_text = raw.full_text.strip()

        # Start with fallbacks, then try AI upgrade
        _build_fallback_summaries(cluster, full_text)

        if full_text and len(full_text) > 300:
            try:
                prompt = f"""You are an expert news summarizer for a Nigerian-focused content app.

Write three summaries from this article text:

1. SHORT (3-4 sentences, minimum 120 characters, 30-60 words)
2. MEDIUM (5-7 sentences, minimum 300 characters, 150-250 words)
3. LONG (15-25 sentences, minimum 1200 characters, 600-1000 words - HIGHLY COMPREHENSIVE with all key facts, context, implications, quotes, statistics, and analysis)

Article text:
{full_text[:25000]}

CRITICAL: The LONG summary MUST be at least 1200 characters and provide extensive coverage including background, key details, quotes, statistics, implications, and future outlook.

Return ONLY:
SHORT: [text]
MEDIUM: [text]
LONG: [text]

Make them engaging, neutral, and suitable for African/Nigerian readers."""

                model = _get_gemini_model()
                response = model.generate_content(prompt)
                _parse_ai_summaries(response.text.strip(), cluster)
                logger.info(f"Gemini summaries generated for cluster {cluster_id}")

            except Exception as e:
                logger.error(f"Gemini summary failed for cluster {cluster_id}: {e}")

        cluster.summary_generated = True
        cluster.save(update_fields=[
            "short_summary", "medium_summary", "long_summary", "summary_generated",
        ])

    except ObjectDoesNotExist:
        logger.warning(f"Cluster {cluster_id} not found for summary generation")
    except Exception as e:
        logger.error(f"Summary generation error for {cluster_id}: {e}")
        raise self.retry(exc=e)


@shared_task(name='content.tasks.generate_event_summary', bind=True, max_retries=2, default_retry_delay=30)
def generate_event_summary(self, event_id):
    """Generate AI-powered summaries for events."""
    try:
        event = Event.objects.get(id=event_id)
        if event.summary_generated:
            return

        short_base = f"{event.canonical_title} at {event.location_name} on {event.start_time.strftime('%B %d, %Y')}"
        event.short_summary = short_base if len(short_base) >= 50 else f"{short_base}. Event."

        if event.description and len(event.description) > 50:
            medium_text = (
                f"{event.canonical_title} at {event.venue_name or event.location_name} "
                f"on {event.start_time.strftime('%B %d')}. {event.description[:200]}..."
            )
        else:
            medium_text = (
                f"{event.canonical_title} is happening at {event.venue_name or event.location_name} "
                f"in {event.location_name} on {event.start_time.strftime('%B %d, %Y at %I:%M %p')}. "
                f"This is a {event.categories[0] if event.categories else 'special'} event you won't want to miss."
            )
        event.medium_summary = medium_text if len(medium_text) >= 100 else f"{medium_text} Get your tickets now!"

        context = f"""Event: {event.canonical_title}
Description: {event.description or 'No description available'}
Venue: {event.venue_name or 'Not specified'}
Location: {event.location_name}
Date: {event.start_time.strftime('%B %d, %Y at %I:%M %p')}
Categories: {', '.join(event.categories) if event.categories else 'General'}"""

        if len(context) >= 200:
            event.long_summary = context
        else:
            enhanced = f"{context}\n\nDon't miss this exciting event in {event.location_name}. "
            enhanced += event.description or "Stay tuned for more details. Mark your calendar and secure your spot."
            event.long_summary = enhanced

        event.summary_generated = True
        event.save(update_fields=["short_summary", "medium_summary", "long_summary", "summary_generated"])
        logger.info(f"Summaries generated for event: {event.canonical_title}")

    except Event.DoesNotExist:
        logger.warning(f"Event {event_id} not found for summary")
    except Exception as e:
        logger.error(f"Event summary generation failed: {e}")
        raise self.retry(exc=e)
