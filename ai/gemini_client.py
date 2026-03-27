import json
import logging
import re
from datetime import datetime, timedelta

import google.generativeai as genai
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.flash = genai.GenerativeModel("gemini-2.5-flash")
        self.pro = genai.GenerativeModel("gemini-2.5-pro")

    def _extract_text(self, response) -> str:
        try:
            return response.text.strip()
        except Exception:
            try:
                if response.candidates:
                    parts = response.candidates[0].content.parts
                    return "".join(p.text for p in parts if hasattr(p, "text")).strip()
            except Exception as e:
                logger.error(f"Text extraction failed: {e}")
        return ""

    def _parse_json(self, text: str) -> dict:
        if not text:
            return {}
        text = re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        logger.warning(f"JSON parse failed: {text[:300]}")
        return {}

    def generate_summaries(self, title: str, full_text: str) -> dict:
        text = full_text[:8000]
        prompt = f"""You are a professional news summarizer.

Title: {title}

Article:
{text}

Return ONLY valid JSON:
{{
  "short": "1-2 sentence summary",
  "medium": "150-300 word summary",
  "long": "400-800 word detailed summary"
}}"""
        try:
            response = self.flash.generate_content(prompt)
            parsed = self._parse_json(self._extract_text(response))
            return {
                "short": parsed.get("short", title)[:300],
                "medium": parsed.get("medium", text[:500] + "...")[:800],
                "long": parsed.get("long", text[:1500] + "...")[:2000],
            }
        except Exception as e:
            logger.error(f"Summary failed: {e}")
            return {"short": title, "medium": "", "long": ""}

    def synthesize_cluster(self, title: str, source_texts: list) -> dict:
        texts = [f"[Source {i+1}]\n{t[:3000]}" for i, t in enumerate(source_texts[:5])]
        combined = "\n\n".join(texts)
        prompt = f"""Synthesize these sources into one insightful overview.

Topic: {title}

Sources:
{combined}

Return ONLY JSON:
{{
  "synthesis": "300-600 word balanced synthesis",
  "key_points": ["Point 1", "Point 2"]
}}"""
        try:
            response = self.pro.generate_content(prompt)
            parsed = self._parse_json(self._extract_text(response))
            return {
                "synthesis": parsed.get("synthesis", f"Multiple sources report on {title}.")[:3000],
                "key_points": parsed.get("key_points", []),
            }
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {"synthesis": "", "key_points": []}

    def answer_question(self, question: str, context: str) -> str:
        prompt = f"""You are Gnoza, an AI news assistant. Answer the user's question based on the article context.

Context:
{context[:6000]}

Question: {question}

Give a clear, accurate, concise answer. If the context doesn't cover the question, say so honestly."""
        try:
            response = self.flash.generate_content(prompt)
            return self._extract_text(response)
        except Exception as e:
            logger.error(f"Q&A failed: {e}")
            return "I couldn't find an answer to that question."

    def deep_dive(self, title: str, full_text: str) -> dict:
        prompt = f"""You are a senior journalist doing a deep-dive analysis.

Title: {title}

Content:
{full_text[:8000]}

Return ONLY valid JSON:
{{
  "analysis": "600-1000 word in-depth analysis",
  "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
  "background_context": "150-300 words of background",
  "implications": "150-300 words on what this means",
  "questions_to_consider": ["question 1", "question 2"]
}}"""
        try:
            response = self.pro.generate_content(prompt)
            return self._parse_json(self._extract_text(response))
        except Exception as e:
            logger.error(f"Deep dive failed: {e}")
            return {}

    def parse_reminder_from_text(self, text: str) -> dict:
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        prompt = f"""You are an AI assistant that parses natural language into structured reminder data.

Current date and time: {current_date}

User input: "{text}"

Return ONLY valid JSON:
{{
  "title": "Brief task/action (max 100 chars)",
  "description": "Additional details if any",
  "reminder_type": "personal|learning|event|tracking|custom",
  "first_reminder_at": "ISO 8601 datetime",
  "recurrence_pattern": "once|daily|weekly|monthly|yearly",
  "metadata": {{}}
}}

Rules:
- If time not specified, use 09:00 (9 AM)
- If date not specified, use tomorrow
- For birthdays set recurrence_pattern to yearly
- Convert relative dates to absolute ISO 8601"""
        try:
            response = self.flash.generate_content(prompt)
            parsed = self._parse_json(self._extract_text(response))
            if not parsed.get("title"):
                parsed["title"] = text[:100]
            if not parsed.get("reminder_type"):
                parsed["reminder_type"] = "custom"
            if not parsed.get("recurrence_pattern"):
                parsed["recurrence_pattern"] = "once"
            if not parsed.get("first_reminder_at"):
                tomorrow = timezone.now() + timedelta(days=1)
                tomorrow = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
                parsed["first_reminder_at"] = tomorrow.isoformat()
            return parsed
        except Exception as e:
            logger.error(f"Reminder parse failed: {e}")
            tomorrow = timezone.now() + timedelta(days=1)
            tomorrow = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            return {
                "title": text[:100],
                "description": "",
                "reminder_type": "custom",
                "first_reminder_at": tomorrow.isoformat(),
                "recurrence_pattern": "once",
                "metadata": {"original_text": text},
            }
