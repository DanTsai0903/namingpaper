"""Ollama provider implementation for local models."""

import base64
import logging

import httpx

from namingpaper.config import get_settings
from namingpaper.models import PDFContent, PaperMetadata
from namingpaper.providers.base import AIProvider, EXTRACTION_PROMPT


class OllamaProvider(AIProvider):
    """Ollama provider for local LLM inference.

    Uses a two-stage approach:
    1. OCR model (deepseek-ocr) extracts text from PDF image
    2. Text model (qwen3:8b) parses metadata from text
    """

    DEFAULT_OCR_MODEL = "deepseek-ocr"
    DEFAULT_TEXT_MODEL = "qwen3:8b"
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
        self._client: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        """Unload models and close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._unload_models()
            await self._client.aclose()
            self._client = None

    async def _unload_models(self) -> None:
        """Tell Ollama to unload models from memory immediately."""
        client = self._get_client()
        for model in {self.text_model, self.ocr_model}:
            try:
                await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": model, "keep_alive": "0s"},
                )
            except httpx.HTTPError:
                pass

    async def __aenter__(self) -> "OllamaProvider":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()

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
            try:
                ocr_text = await self._ocr_extract(content.first_page_image)
                combined_text = f"{ocr_text}\n\n{content.text}" if content.text else ocr_text
            except RuntimeError:
                logging.getLogger(__name__).warning(
                    "OCR model unavailable, falling back to text-only extraction"
                )
                combined_text = content.text or ""
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

        return self._parse_response_json(response_text, "Ollama")

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create a reusable async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client

    async def _call_ollama(self, endpoint: str, payload: dict) -> dict:
        """Make a request to Ollama API."""
        try:
            client = self._get_client()
            response = await client.post(
                f"{self.base_url}{endpoint}",
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            model = payload.get("model", "unknown")
            if e.response.status_code == 404:
                raise RuntimeError(
                    f"Model '{model}' not found in Ollama.\n\n"
                    f"Pull it with: ollama pull {model}\n\n"
                    f"Required model:\n"
                    f"  - {self.text_model} (text parsing)\n\n"
                    f"Optional (for scanned PDFs):\n"
                    f"  - {self.ocr_model} (OCR)"
                ) from e
            raise RuntimeError(
                f"Ollama API error: {e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}.\n\n"
                f"Ollama is required for the default provider. To set up:\n"
                f"  1. Install Ollama: https://ollama.com/download\n"
                f"  2. Start the server: ollama serve\n"
                f"  3. Pull the text model: ollama pull {self.text_model}\n"
                f"  4. (Optional, for scanned PDFs) ollama pull {self.ocr_model}\n\n"
                f"Or use a different provider: namingpaper rename --provider claude <file>"
            )
        except httpx.ReadTimeout:
            model = payload.get("model", "unknown")
            raise RuntimeError(
                f"Ollama timed out after 300s. The model '{model}' may be too slow."
            )

        return response.json()
