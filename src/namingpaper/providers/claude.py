"""Anthropic Claude provider implementation."""

import base64
import json

import anthropic

from namingpaper.config import get_settings
from namingpaper.models import PDFContent, PaperMetadata
from namingpaper.providers.base import AIProvider, EXTRACTION_PROMPT


class ClaudeProvider(AIProvider):
    """Claude AI provider using Anthropic's API."""

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, api_key: str, model: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL

    async def extract_metadata(self, content: PDFContent) -> PaperMetadata:
        """Extract metadata using Claude."""
        settings = get_settings()
        text = self._truncate_text(content.text, settings.max_text_chars)

        # Build message content
        message_content: list[dict] = []

        # Add image if available (Claude supports vision)
        if content.first_page_image:
            image_data = base64.standard_b64encode(content.first_page_image).decode(
                "utf-8"
            )
            message_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_data,
                    },
                }
            )

        # Add text
        message_content.append(
            {
                "type": "text",
                "text": f"Paper text:\n\n{text}",
            }
        )

        # Call Claude API (sync, but wrapped for async interface)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": message_content,
                },
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT,
                },
            ],
        )

        # Parse response
        response_text = response.content[0].text

        # Extract JSON from response (handle potential markdown code blocks)
        json_text = response_text
        if "```json" in response_text:
            json_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_text = response_text.split("```")[1].split("```")[0]

        try:
            data = json.loads(json_text.strip())
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse JSON from Claude response: {e}\nResponse: {response_text[:500]}"
            ) from e

        return PaperMetadata(**data)
