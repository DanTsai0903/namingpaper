"""Data models for namingpaper."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class PaperMetadata(BaseModel):
    """Metadata extracted from an academic paper."""

    authors: list[str] = Field(description="List of author last names")
    authors_full: list[str] = Field(
        default_factory=list, description="List of author full names"
    )
    year: int = Field(description="Publication year")
    journal: str = Field(description="Full journal name")
    journal_abbrev: str | None = Field(
        default=None, description="Common journal abbreviation"
    )
    title: str = Field(description="Paper title")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence score"
    )


class LowConfidenceError(Exception):
    """Raised when extraction confidence is below the minimum threshold."""

    def __init__(self, confidence: float, threshold: float):
        self.confidence = confidence
        self.threshold = threshold
        super().__init__(
            f"Confidence {confidence:.0%} is below threshold {threshold:.0%}. "
            "The document may not be an academic paper."
        )


class PDFContent(BaseModel):
    """Content extracted from a PDF file."""

    text: str = Field(description="Extracted text from PDF")
    first_page_image: bytes | None = Field(
        default=None, description="First page as image bytes (PNG)"
    )
    path: Path = Field(description="Original file path")

    model_config = {"arbitrary_types_allowed": True}


class RenameOperation(BaseModel):
    """Represents a file rename operation."""

    source: Path = Field(description="Original file path")
    destination: Path = Field(description="New file path")
    metadata: PaperMetadata = Field(description="Extracted metadata")

    model_config = {"arbitrary_types_allowed": True}


class BatchItemStatus(str, Enum):
    """Status of a batch item."""

    PENDING = "pending"
    OK = "ok"
    COLLISION = "collision"
    ERROR = "error"
    SKIPPED = "skipped"
    COMPLETED = "completed"


class BatchItem(BaseModel):
    """A single item in a batch operation."""

    source: Path = Field(description="Original file path")
    destination: Path | None = Field(default=None, description="Planned destination")
    metadata: PaperMetadata | None = Field(default=None, description="Extracted metadata")
    status: BatchItemStatus = Field(default=BatchItemStatus.PENDING)
    error: str | None = Field(default=None, description="Error message if failed")

    model_config = {"arbitrary_types_allowed": True}


class BatchResult(BaseModel):
    """Result of a batch operation."""

    total: int = Field(description="Total files processed")
    successful: int = Field(default=0, description="Successfully renamed")
    skipped: int = Field(default=0, description="Skipped due to collision or user choice")
    errors: int = Field(default=0, description="Failed with errors")
    items: list[BatchItem] = Field(default_factory=list, description="Individual results")
