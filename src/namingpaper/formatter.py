"""Filename formatting from metadata."""

import re
import unicodedata
from pathlib import Path

from namingpaper.config import get_settings
from namingpaper.models import PaperMetadata


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    # Normalize unicode
    name = unicodedata.normalize("NFKD", name)
    # Remove control characters
    name = "".join(c for c in name if not unicodedata.category(c).startswith("C"))
    # Replace path separators and other problematic characters
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    # Replace multiple spaces/underscores with single underscore
    name = re.sub(r"[\s_]+", " ", name)
    # Strip leading/trailing whitespace and dots
    name = name.strip(". ")
    return name


def format_authors(authors: list[str], max_authors: int = 3) -> str:
    """Format author list for filename.

    Examples:
        ["Smith"] -> "Smith"
        ["Smith", "Jones"] -> "Smith and Jones"
        ["Smith", "Jones", "Brown"] -> "Smith, Jones, and Brown"
        ["Smith", "Jones", "Brown", "Davis"] -> "Smith et al"
    """
    if not authors:
        return "Unknown"

    if len(authors) > max_authors:
        return f"{authors[0]} et al"
    elif len(authors) == 1:
        return authors[0]
    elif len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    else:
        return ", ".join(authors[:-1]) + f", and {authors[-1]}"


def format_journal(journal: str, journal_abbrev: str | None) -> str:
    """Format journal for filename, preferring abbreviation."""
    return journal_abbrev or journal


def format_title(title: str, max_words: int = 6) -> str:
    """Format title for filename, truncating if needed."""
    # Take first N words
    words = title.split()[:max_words]
    result = " ".join(words)
    # Add ellipsis if truncated
    if len(title.split()) > max_words:
        result = result.rstrip(".,;:") + "..."
    return result


def build_filename(
    metadata: PaperMetadata,
    max_authors: int | None = None,
    max_filename_length: int | None = None,
) -> str:
    """Build filename from paper metadata.

    Format: author names_(year, journal abbrev)_topic.pdf

    Examples:
        "Fama, French_(1993, JFE)_Common risk factors.pdf"
        "Smith et al_(2020, AER)_Economic impacts of climate....pdf"
    """
    settings = get_settings()
    max_authors = max_authors or settings.max_authors
    max_filename_length = max_filename_length or settings.max_filename_length

    authors_str = format_authors(metadata.authors, max_authors)
    journal_str = format_journal(metadata.journal, metadata.journal_abbrev)
    title_str = format_title(metadata.title)

    # Build the filename
    filename = f"{authors_str}, ({metadata.year}, {journal_str}), {title_str}.pdf"

    # Sanitize
    filename = sanitize_filename(filename)

    # Truncate if too long (preserve .pdf extension)
    if len(filename) > max_filename_length:
        filename = filename[: max_filename_length - 4] + ".pdf"

    return filename


def build_destination(source: Path, metadata: PaperMetadata) -> Path:
    """Build full destination path for renamed file."""
    filename = build_filename(metadata)
    return source.parent / filename
