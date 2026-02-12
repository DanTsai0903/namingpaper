"""Filename formatting from metadata."""

import re
import unicodedata
from pathlib import Path

from namingpaper.config import get_settings
from namingpaper.models import PaperMetadata

_RE_INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')
_RE_WHITESPACE = re.compile(r"[\s_]+")


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    # Normalize unicode (skip for pure ASCII)
    if not name.isascii():
        name = unicodedata.normalize("NFKD", name)
        # Remove control characters
        name = "".join(c for c in name if not unicodedata.category(c).startswith("C"))
    # Replace path separators and other problematic characters
    name = _RE_INVALID_CHARS.sub("", name)
    # Replace multiple spaces/underscores with single space
    name = _RE_WHITESPACE.sub(" ", name)
    # Strip leading/trailing whitespace and dots
    name = name.strip(". ")
    return name


def _format_name_list(names: list[str], max_names: int = 3) -> str:
    """Format a list of names with Oxford comma rules.

    Examples:
        ["Smith"] -> "Smith"
        ["Smith", "Jones"] -> "Smith and Jones"
        ["Smith", "Jones", "Brown"] -> "Smith, Jones, and Brown"
        ["Smith", "Jones", "Brown", "Davis"] -> "Smith et al"
    """
    if not names:
        return "Unknown"

    if len(names) > max_names:
        return f"{names[0]} et al"
    elif len(names) == 1:
        return names[0]
    elif len(names) == 2:
        return f"{names[0]} and {names[1]}"
    else:
        return ", ".join(names[:-1]) + f", and {names[-1]}"


def format_authors(authors: list[str], max_authors: int = 3) -> str:
    """Format author last names for filename."""
    return _format_name_list(authors, max_authors)


def format_authors_full(authors_full: list[str], max_authors: int = 3) -> str:
    """Format full author names for filename."""
    return _format_name_list(authors_full, max_authors)


def _abbreviate_name(full_name: str) -> str:
    """Convert a full name to surname with initials.

    Examples:
        "Eugene F. Fama" -> "Fama, E. F."
        "Kenneth R. French" -> "French, K. R."
        "Fama" -> "Fama"
    """
    parts = full_name.strip().split()
    if len(parts) <= 1:
        return full_name
    surname = parts[-1]
    initials = " ".join(f"{p[0]}." for p in parts[:-1])
    return f"{surname}, {initials}"


def format_authors_abbrev(authors_full: list[str], max_authors: int = 3) -> str:
    """Format authors as surname with initials.

    Examples:
        ["Eugene F. Fama", "Kenneth R. French"] -> "Fama, E. F. and French, K. R."
    """
    abbreviated = [_abbreviate_name(name) for name in authors_full]
    return _format_name_list(abbreviated, max_authors)


def format_journal(journal: str, journal_abbrev: str | None) -> str:
    """Format journal for filename, preferring abbreviation."""
    return journal_abbrev or journal


def format_title(title: str, max_words: int = 6) -> str:
    """Format title for filename, truncating if needed."""
    # Take first N words
    all_words = title.split()
    words = all_words[:max_words]
    result = " ".join(words)
    # Add ellipsis if truncated
    if len(all_words) > max_words:
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
        truncated = filename[: max_filename_length - 4].rstrip(". ")
        filename = truncated + ".pdf"

    return filename


def build_destination(source: Path, metadata: PaperMetadata) -> Path:
    """Build full destination path for renamed file."""
    filename = build_filename(metadata)
    return source.parent / filename
