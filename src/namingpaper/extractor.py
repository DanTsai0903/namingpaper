"""Orchestrates PDF reading and AI metadata extraction."""

import asyncio
from pathlib import Path

from namingpaper.config import get_settings
from namingpaper.models import LowConfidenceError, PDFContent, PaperMetadata, RenameOperation
from namingpaper.pdf_reader import extract_pdf_content
from namingpaper.formatter import build_destination
from namingpaper.providers import get_provider
from namingpaper.providers.base import AIProvider


async def extract_metadata(
    pdf_path: Path,
    provider: AIProvider | None = None,
    provider_name: str | None = None,
    model_name: str | None = None,
    ocr_model: str | None = None,
    keep_alive: str | None = None,
) -> PaperMetadata:
    """Extract metadata from a PDF file.

    Args:
        pdf_path: Path to the PDF file
        provider: Pre-initialized AI provider (optional)
        provider_name: Name of provider to use if provider not given
        model_name: Override the default model for the provider
        ocr_model: Override the Ollama OCR model
        keep_alive: Ollama keep_alive duration (e.g., "60s", "0s")

    Returns:
        Extracted paper metadata
    """
    # Get provider
    if provider is None:
        provider = get_provider(provider_name, model_name=model_name, ocr_model=ocr_model, keep_alive=keep_alive)

    # Extract PDF content
    content = extract_pdf_content(pdf_path)

    # Extract metadata using AI
    metadata = await provider.extract_metadata(content)

    # Check confidence threshold
    settings = get_settings()
    if metadata.confidence < settings.min_confidence:
        raise LowConfidenceError(metadata.confidence, settings.min_confidence)

    return metadata


async def plan_rename(
    pdf_path: Path,
    provider: AIProvider | None = None,
    provider_name: str | None = None,
    model_name: str | None = None,
    ocr_model: str | None = None,
    keep_alive: str | None = None,
) -> RenameOperation:
    """Plan a rename operation for a PDF file.

    Args:
        pdf_path: Path to the PDF file
        provider: Pre-initialized AI provider (optional)
        provider_name: Name of provider to use if provider not given
        model_name: Override the default model for the provider
        ocr_model: Override the Ollama OCR model
        keep_alive: Ollama keep_alive duration (e.g., "60s", "0s")

    Returns:
        Planned rename operation with metadata
    """
    metadata = await extract_metadata(pdf_path, provider, provider_name, model_name=model_name, ocr_model=ocr_model, keep_alive=keep_alive)
    destination = build_destination(pdf_path, metadata)

    return RenameOperation(
        source=pdf_path,
        destination=destination,
        metadata=metadata,
    )


def plan_rename_sync(
    pdf_path: Path,
    provider: AIProvider | None = None,
    provider_name: str | None = None,
    model_name: str | None = None,
    ocr_model: str | None = None,
    keep_alive: str | None = None,
) -> RenameOperation:
    """Synchronous wrapper for plan_rename."""
    return asyncio.run(plan_rename(pdf_path, provider, provider_name, model_name=model_name, ocr_model=ocr_model, keep_alive=keep_alive))
