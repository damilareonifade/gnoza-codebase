import logging
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from gnoza.response import Ok, BadRequest, NotFound
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..models import ContentChat
from ..serializers import ContentChatSerializer
from .ai_analysis import _get_content_text

logger = logging.getLogger(__name__)


class ContentChatView(APIView):
    """
    GET  /api/v1/content/chat/<content_id>/  — retrieve chat history
    POST /api/v1/content/chat/<content_id>/  — send a message and get an AI reply
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ContentChatSerializer

    @extend_schema(responses=OpenApiResponse(description="Chat history"))
    def get(self, request, content_id):
        title, _ = _get_content_text(content_id)
        if not title:
            return NotFound("Content not found.")

        chat = ContentChat.objects.filter(
            user=request.user, content_id=content_id
        ).first()
        if not chat:
            return Ok("No chat history", {"messages": []})
        return Ok("Chat history", ContentChatSerializer(chat).data)

    @extend_schema(request=None, responses=OpenApiResponse(description="Chat message sent"))
    def post(self, request, content_id):
        user_message = (request.data.get("text") or "").strip()
        if not user_message:
            return BadRequest("Message text is required.")

        title, full_text = _get_content_text(content_id)
        if not title:
            return NotFound("Content not found.")

        chat, _ = ContentChat.objects.get_or_create(
            user=request.user, content_id=content_id
        )
        chat.messages.append({"role": "user", "text": user_message})

        ai_text = self._generate_ai_response(user_message, chat, title, full_text)
        chat.messages.append({"role": "ai", "text": ai_text})
        chat.save()

        return Ok("Message sent", ContentChatSerializer(chat).data)

    def _generate_ai_response(self, user_message: str, chat: ContentChat, title: str, full_text: str) -> str:
        try:
            from django.conf import settings
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                "gemini-2.5-flash",
                system_instruction=(
                    "You are Gnoza, an assistant discussing the following content with the user. "
                    f"Title: {title}\n\nContent:\n{full_text[:6000]}"
                ),
            )

            history = chat.messages[-10:]
            gemini_history = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg["text"]]})

            response = model.generate_content(gemini_history)
            text = response.text.strip() if hasattr(response, "text") else str(response)
            return text or "Sorry, I couldn't generate a response right now."
        except Exception as exc:
            logger.error(f"Gemini chat error: {exc}")
            return "Sorry, I couldn't generate a response right now."


class NarrateAIResponseView(APIView):
    """
    POST /api/v1/content/chat/<content_id>/narrate/
    Convert the latest AI chat response to speech (MP3).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=OpenApiResponse(description="Audio narration of AI response"))
    def post(self, request, content_id):
        chat = ContentChat.objects.filter(
            user=request.user, content_id=content_id
        ).first()
        if not chat or not chat.messages:
            return BadRequest("No chat history found.")

        ai_message = next(
            (m["text"] for m in reversed(chat.messages) if m["role"] == "ai"), None
        )
        if not ai_message:
            return BadRequest("No AI response to narrate.")

        try:
            import google.cloud.texttospeech as tts

            client = tts.TextToSpeechClient()
            synthesis_input = tts.SynthesisInput(text=ai_message)
            voice = tts.VoiceSelectionParams(
                language_code="en-US",
                ssml_gender=tts.SsmlVoiceGender.NEUTRAL,
            )
            audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.MP3)
            tts_response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            return HttpResponse(tts_response.audio_content, content_type="audio/mpeg")
        except Exception as exc:
            logger.error(f"TTS error: {exc}")
            return BadRequest("Text-to-speech service unavailable.")
