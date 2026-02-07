"""Google Gemini provider implementation."""

import json

from namingpaper.config import get_settings
from namingpaper.models import PDFContent, PaperMetadata
from namingpaper.providers.base import AIProvider, EXTRACTION_PROMPT

try:
    import google.generativeai as genai
    from PIL import Image
    import io

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(self, api_key: str, model: str | None = None):
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "Gemini package not installed. Run: pip install namingpaper[gemini]"
            )
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model or self.DEFAULT_MODEL)

    async def extract_metadata(self, content: PDFContent) -> PaperMetadata:
        """Extract metadata using Gemini."""
        settings = get_settings()
        text = self._truncate_text(content.text, settings.max_text_chars)

        # Build prompt parts
        parts = []

        # Add image if available
        if content.first_page_image:
            image = Image.open(io.BytesIO(content.first_page_image))
            parts.append(image)

        # Add text and prompt
        parts.append(f"Paper text:\n\n{text}\n\n{EXTRACTION_PROMPT}")

        # Call Gemini API
        try:
            response = self.model.generate_content(parts)
        except Exception as e:
            err = str(e).lower()
            if "not found" in err or "404" in err or "does not exist" in err:
                raise RuntimeError(
                    f"Model not found. Check available models at https://ai.google.dev/gemini-api/docs/models"
                ) from e
            if "api key" in err or "permission" in err:
                raise RuntimeError(
                    "Invalid Gemini API key. Check your NAMINGPAPER_GEMINI_API_KEY."
                ) from e
            raise

        # Parse response
        response_text = response.text

        # Extract JSON from response
        json_text = response_text
        if "```json" in response_text:
            json_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_text = response_text.split("```")[1].split("```")[0]

        try:
            data = json.loads(json_text.strip())
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse JSON from Gemini response: {e}\nResponse: {response_text[:500]}"
            ) from e

        return PaperMetadata(**data)
