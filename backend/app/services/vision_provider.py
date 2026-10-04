"""Multimodal provider abstraction for the Vision Agent.

The execution plan targets Gemini; the Colab prototype runs on Groq.
Both implement analyse_image(); switch via VISION_PROVIDER env var.
"""
import base64
from abc import ABC, abstractmethod

from ..config import Settings
from ..utils.json_utils import safe_json
from ..utils.retry import with_retry

VISION_PROMPT = (
    "You analyse ONE frame from a video. Reply with ONLY a JSON object with keys:\n"
    '"frame_type": one of ["slide","code","chart","talking_head","other"],\n'
    '"ocr_text": all legible on-screen text (slide titles, bullets, code, formulas) or "" if none,\n'
    '"description": 1-2 sentences describing diagrams/charts/demos (empty string for talking_head),\n'
    '"confidence": your confidence in this analysis, a number from 0.0 to 1.0.\n'
    "Do not add any text outside the JSON."
)


class VisionProvider(ABC):
    @abstractmethod
    def analyse_image(self, image_path: str) -> dict:
        """Return {frame_type, ocr_text, description, confidence} for one frame."""


class GroqVisionProvider(VisionProvider):
    def __init__(self, settings: Settings):
        from groq import Groq
        self.client = Groq(api_key=settings.groq_api_key, max_retries=0)
        self.model = settings.vision_model_groq

    def analyse_image(self, image_path: str) -> dict:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        def go():
            r = self.client.chat.completions.create(
                model=self.model, temperature=0.1, max_tokens=700,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url",
                     "image_url": {"url": "data:image/jpeg;base64," + b64}},
                ]}])
            return r.choices[0].message.content

        return safe_json(with_retry(go, label="vision/groq"))


class GeminiVisionProvider(VisionProvider):
    def __init__(self, settings: Settings):
        from google import genai
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.vision_model_gemini

    def analyse_image(self, image_path: str) -> dict:
        from google.genai import types
        with open(image_path, "rb") as f:
            data = f.read()

        def go():
            r = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=data, mime_type="image/jpeg"),
                    VISION_PROMPT,
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1, response_mime_type="application/json"),
            )
            return r.text

        return safe_json(with_retry(go, label="vision/gemini"))


class NullVisionProvider(VisionProvider):
    """Offline mode: no VLM calls. EasyOCR still runs, so sampling/dedupe/OCR
    can be developed and tested without an API key or quota."""

    def analyse_image(self, image_path: str) -> dict:
        return {}


def get_vision_provider(settings: Settings) -> VisionProvider:
    name = settings.vision_provider.lower()
    if name == "gemini":
        return GeminiVisionProvider(settings)
    if name == "groq":
        return GroqVisionProvider(settings)
    if name == "none":
        return NullVisionProvider()
    raise ValueError(
        f"Unknown VISION_PROVIDER: {settings.vision_provider!r} (use 'gemini', 'groq' or 'none')")
