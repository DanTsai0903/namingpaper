"""PDF content extraction."""

import io
from pathlib import Path

import pdfplumber
from PIL import Image

from namingpaper.models import PDFContent


class PDFReadError(Exception):
    """Error reading or processing PDF file."""

    pass


def extract_pdf_content(
    pdf_path: Path,
    max_pages: int = 2,
    extract_image: bool = True,
) -> PDFContent:
    """Extract text and optionally first page image from a PDF.

    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to extract text from
        extract_image: Whether to extract first page as image

    Returns:
        PDFContent with extracted text and optional image

    Raises:
        PDFReadError: If the PDF cannot be read or is corrupted
    """
    text_parts: list[str] = []
    first_page_image: bytes | None = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                raise PDFReadError(f"PDF has no pages: {pdf_path}")

            # Extract text from first N pages
            for i, page in enumerate(pdf.pages[:max_pages]):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    # Continue with other pages if one fails
                    pass

            # Extract first page as image
            if extract_image and pdf.pages:
                try:
                    first_page = pdf.pages[0]
                    # Convert to PIL Image
                    img = first_page.to_image(resolution=150)
                    # Save to bytes
                    buffer = io.BytesIO()
                    img.original.save(buffer, format="PNG")
                    first_page_image = buffer.getvalue()
                except Exception as e:
                    # Image extraction failed, continue without image
                    first_page_image = None

    except PDFReadError:
        raise
    except Exception as e:
        raise PDFReadError(f"Failed to read PDF '{pdf_path}': {e}") from e

    if not text_parts and not first_page_image:
        raise PDFReadError(f"Could not extract any content from PDF: {pdf_path}")

    return PDFContent(
        text="\n\n".join(text_parts),
        first_page_image=first_page_image,
        path=pdf_path,
    )


def extract_text_only(pdf_path: Path, max_pages: int = 2) -> str:
    """Extract only text from a PDF (faster, no image processing)."""
    content = extract_pdf_content(pdf_path, max_pages=max_pages, extract_image=False)
    return content.text
