import logging
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gnoza.response import Ok, BadRequest
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..models import ContentCluster, Event

logger = logging.getLogger(__name__)


def _get_content_text(content_id: str) -> tuple[str, str]:
    """Return (title, full_text) for a given content_id (cluster or event)."""
    cluster = ContentCluster.objects.filter(id=content_id).first()
    if cluster:
        return cluster.canonical_title, cluster.get_full_text()
    event = Event.objects.filter(id=content_id).first()
    if event:
        return event.canonical_title, event.description or event.canonical_title
    return "", ""


class DeepDiveView(APIView):
    """
    GET /api/v1/content/deep-dive/<content_id>/
    Return an AI-generated deep-dive analysis of a content item.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiResponse(description="AI deep-dive analysis"))
    def get(self, request, content_id):
        title, full_text = _get_content_text(content_id)
        if not title:
            return BadRequest("Content not found.")

        try:
            from django.conf import settings
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = f"""
You are an expert analyst. Provide a comprehensive deep-dive analysis of the following content.

Title: {title}

Content:
{full_text[:6000]}

Provide:
1. Key themes and main points
2. Background context and significance
3. Different perspectives or angles
4. Potential implications or impact
5. Related topics to explore

Be thorough, insightful, and objective.
"""
            response = model.generate_content(prompt)
            analysis = response.text.strip() if hasattr(response, "text") else ""
            return Ok("Deep dive analysis", {"content_id": str(content_id), "analysis": analysis})
        except Exception as exc:
            logger.error(f"DeepDive error: {exc}")
            return Response({"error": "AI analysis temporarily unavailable."}, status=503)


class AskGnozaView(APIView):
    """
    POST /api/v1/content/ask-gnoza/<content_id>/
    Ask a freeform question about a content item.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=OpenApiResponse(description="AI answer to user question"))
    def post(self, request, content_id):
        question = (request.data.get("question") or "").strip()
        if not question:
            return BadRequest("question is required.")

        title, full_text = _get_content_text(content_id)
        if not title:
            return BadRequest("Content not found.")

        try:
            from django.conf import settings
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = f"""
You are Gnoza, an intelligent news and events assistant. Answer the following question based on the provided content.

Title: {title}

Content:
{full_text[:5000]}

User Question: {question}

Provide a clear, accurate, and helpful answer. If the content doesn't contain enough information to answer the question fully, say so and provide what context you can.
"""
            response = model.generate_content(prompt)
            answer = response.text.strip() if hasattr(response, "text") else ""
            return Ok(
                "Answer",
                {
                    "content_id": str(content_id),
                    "question": question,
                    "answer": answer,
                },
            )
        except Exception as exc:
            logger.error(f"AskGnoza error: {exc}")
            return Response({"error": "AI service temporarily unavailable."}, status=503)
