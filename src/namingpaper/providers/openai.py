"""OpenAI provider implementation."""

import base64

from namingpaper.config import get_settings
from namingpaper.models import PDFContent, PaperMetadata
from namingpaper.providers.base import AIProvider, EXTRACTION_PROMPT

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


class OpenAIProvider(AIProvider):
    """OpenAI provider using GPT models."""

    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, api_key: str, model: str | None = None):
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. Run: pip install namingpaper[openai]"
            )
        self.client = OpenAI(api_key=api_key, timeout=120.0)
        self.model = model or self.DEFAULT_MODEL

    async def extract_metadata(self, content: PDFContent) -> PaperMetadata:
        """Extract metadata using OpenAI."""
        settings = get_settings()
        text = self._truncate_text(content.text, settings.max_text_chars)

        # Build message content
        message_content: list[dict] = []

        # Add text first
        message_content.append(
            {
                "type": "text",
                "text": f"Paper text:\n\n{text}\n\n{EXTRACTION_PROMPT}",
            }
        )

        # Add image if available
        if content.first_page_image:
            image_data = base64.standard_b64encode(content.first_page_image).decode(
                "utf-8"
            )
            message_content.insert(
                0,
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_data}",
                    },
                },
            )

        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": message_content,
                    },
                ],
            )
        except Exception as e:
            err = str(e).lower()
            if "model" in err and ("not found" in err or "does not exist" in err):
                raise RuntimeError(
                    f"Model '{self.model}' not found. Check available models at https://platform.openai.com/docs/models"
                ) from e
            if "auth" in err or "api key" in err:
                raise RuntimeError(
                    "Invalid OpenAI API key. Check your NAMINGPAPER_OPENAI_API_KEY."
                ) from e
            raise

        # Parse response
        if not response.choices or not response.choices[0].message.content:
            raise RuntimeError("OpenAI returned an empty response.")
        response_text = response.choices[0].message.content

        return self._parse_response_json(response_text, "OpenAI")
