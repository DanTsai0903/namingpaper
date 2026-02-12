"""PDF content extraction."""

import logging
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

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

    doc = None
    try:
        doc = fitz.open(pdf_path)
        if not doc.page_count:
            raise PDFReadError(f"PDF has no pages: {pdf_path}")

        # Extract text from first N pages
        for i in range(min(max_pages, doc.page_count)):
            try:
                page_text = doc[i].get_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                logger.debug("Failed to extract text from page %d of %s: %s", i, pdf_path, e)

        # Extract first page as image
        if extract_image and doc.page_count:
            try:
                pix = doc[0].get_pixmap(dpi=150)
                first_page_image = pix.tobytes("png")
            except Exception as e:
                logger.debug("Failed to extract image from %s: %s", pdf_path, e)
                first_page_image = None

    except PDFReadError:
        raise
    except Exception as e:
        raise PDFReadError(f"Failed to read PDF '{pdf_path}': {e}") from e
    finally:
        if doc is not None:
            doc.close()

    if not text_parts and not first_page_image:
        raise PDFReadError(f"Could not extract any content from PDF: {pdf_path}")

    return PDFContent(
        text="\n\n".join(text_parts),
        first_page_image=first_page_image,
        path=pdf_path,
    )


def extract_text_only(pdf_path: Path, max_pages: int = 2) -> str:
    """Extract only text from a PDF (no image processing)."""
    content = extract_pdf_content(pdf_path, max_pages=max_pages, extract_image=False)
    return content.text
