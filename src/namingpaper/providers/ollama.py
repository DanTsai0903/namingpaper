"""Ollama provider implementation for local models."""

import base64
import json

import httpx

from namingpaper.config import get_settings
from namingpaper.models import PDFContent, PaperMetadata
from namingpaper.providers.base import AIProvider, EXTRACTION_PROMPT


class OllamaProvider(AIProvider):
    """Ollama provider for local LLM inference.

    Uses a two-stage approach:
    1. OCR model (deepseek-ocr) extracts text from PDF image
    2. Text model (llama3.1:8b) parses metadata from text
    """

    DEFAULT_OCR_MODEL = "deepseek-ocr"
    DEFAULT_TEXT_MODEL = "llama3.1:8b"
    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        ocr_model: str | None = None,
        text_model: str | None = None,
        keep_alive: str = "0s",
    ):
        # For backwards compatibility, model param sets text_model
        self.ocr_model = ocr_model or self.DEFAULT_OCR_MODEL
        self.text_model = text_model or model or self.DEFAULT_TEXT_MODEL
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.keep_alive = keep_alive

    async def extract_metadata(self, content: PDFContent) -> PaperMetadata:
        """Extract metadata using Ollama pipeline.

        If text extraction already produced usable text, skip the slow OCR stage
        and go straight to metadata parsing. Only fall back to OCR when text is
        missing or too short to be useful.
        """
        settings = get_settings()

        if content.text and len(content.text.strip()) > 100:
            combined_text = content.text
        elif content.first_page_image:
            ocr_text = await self._ocr_extract(content.first_page_image)
            combined_text = f"{ocr_text}\n\n{content.text}" if content.text else ocr_text
        else:
            combined_text = content.text

        # Stage 2: Parse metadata using text model
        text = self._truncate_text(combined_text, settings.max_text_chars)
        return await self._parse_metadata(text)

    async def _ocr_extract(self, image_data: bytes) -> str:
        """Stage 1: Extract text from image using OCR model."""
        image_b64 = base64.standard_b64encode(image_data).decode("utf-8")

        payload = {
            "model": self.ocr_model,
            "messages": [
                {
                    "role": "user",
                    "content": "Extract all text from this academic paper image. Include title, authors, abstract, and any visible text.",
                    "images": [image_b64],
                }
            ],
            "stream": False,
            "keep_alive": self.keep_alive,
        }

        result = await self._call_ollama("/api/chat", payload)

        if "message" in result:
            return result["message"].get("content", "")
        return result.get("response", "")

    async def _parse_metadata(self, text: str) -> PaperMetadata:
        """Stage 2: Parse metadata from text using text model."""
        prompt = f"Paper text:\n\n{text}\n\n{EXTRACTION_PROMPT}"

        payload = {
            "model": self.text_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "keep_alive": self.keep_alive,
        }

        result = await self._call_ollama("/api/generate", payload)
        response_text = result.get("response", "")

        if not response_text:
            raise RuntimeError(
                f"Ollama returned empty response. Model '{self.text_model}' may not be available. "
                f"Run: ollama pull {self.text_model}"
            )

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
                f"Failed to parse JSON from Ollama response: {e}\nResponse: {response_text[:500]}"
            ) from e

        return PaperMetadata(**data)

    async def _call_ollama(self, endpoint: str, payload: dict) -> dict:
        """Make a request to Ollama API."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            model = payload.get("model", "unknown")
            if e.response.status_code == 404:
                raise RuntimeError(
                    f"Model '{model}' not found. Pull it first with: ollama pull {model}"
                ) from e
            raise RuntimeError(
                f"Ollama API error: {e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. Is Ollama running?"
            )
        except httpx.ReadTimeout:
            model = payload.get("model", "unknown")
            raise RuntimeError(
                f"Ollama timed out after 300s. The model '{model}' may be too slow."
            )

        return response.json()
