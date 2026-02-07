"""Template-based filename formatting."""

import re
from typing import Callable

from namingpaper.models import PaperMetadata
from namingpaper.formatter import (
    format_authors,
    format_journal,
    format_title,
    sanitize_filename,
)
from namingpaper.config import get_settings


# Preset templates
PRESET_TEMPLATES: dict[str, str] = {
    "default": "{authors}, ({year}, {journal}), {title}",
    "compact": "{authors} ({year}) {title}",
    "full": "{authors}, ({year}, {journal_full}), {title}",
    "simple": "{authors}_{year}_{title}",
}


def get_template(template_or_name: str) -> str:
    """Get template string from preset name or return as-is.

    Args:
        template_or_name: Either a preset name (default, compact, full, simple)
                         or a custom template string with placeholders

    Returns:
        Template string with placeholders
    """
    return PRESET_TEMPLATES.get(template_or_name, template_or_name)


def validate_template(template: str) -> tuple[bool, str | None]:
    """Validate a template string.

    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_placeholders = {
        "authors", "year", "journal", "journal_abbrev",
        "journal_full", "title"
    }

    # Find all placeholders in template
    found = re.findall(r"\{(\w+)\}", template)

    if not found:
        return False, "Template must contain at least one placeholder"

    for placeholder in found:
        if placeholder not in valid_placeholders:
            return False, f"Invalid placeholder: {{{placeholder}}}. Valid: {valid_placeholders}"

    return True, None


def build_filename_from_template(
    metadata: PaperMetadata,
    template: str,
    max_authors: int | None = None,
    max_filename_length: int | None = None,
) -> str:
    """Build filename from metadata using a template.

    Template placeholders:
        {authors} - Formatted author list (respects max_authors)
        {year} - Publication year
        {journal} - Journal abbreviation (or full name if no abbrev)
        {journal_abbrev} - Journal abbreviation only (empty if none)
        {journal_full} - Full journal name
        {title} - Truncated title

    Args:
        metadata: Paper metadata
        template: Template string or preset name
        max_authors: Maximum authors before "et al"
        max_filename_length: Maximum filename length

    Returns:
        Formatted filename with .pdf extension
    """
    settings = get_settings()
    max_authors = max_authors or settings.max_authors
    max_filename_length = max_filename_length or settings.max_filename_length

    # Resolve preset
    template = get_template(template)

    # Build replacement values
    replacements: dict[str, str] = {
        "authors": format_authors(metadata.authors, max_authors),
        "year": str(metadata.year),
        "journal": format_journal(metadata.journal, metadata.journal_abbrev),
        "journal_abbrev": metadata.journal_abbrev or "",
        "journal_full": metadata.journal,
        "title": format_title(metadata.title),
    }

    # Apply replacements
    filename = template
    for key, value in replacements.items():
        filename = filename.replace(f"{{{key}}}", value)

    # Add extension
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    # Sanitize
    filename = sanitize_filename(filename)

    # Truncate if too long
    if len(filename) > max_filename_length:
        filename = filename[:max_filename_length - 4] + ".pdf"

    return filename


def list_presets() -> dict[str, str]:
    """Return available preset templates."""
    return PRESET_TEMPLATES.copy()
