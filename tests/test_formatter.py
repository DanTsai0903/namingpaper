"""Tests for filename formatting."""

import pytest

from namingpaper.formatter import (
    build_filename,
    format_authors,
    format_journal,
    format_title,
    sanitize_filename,
)
from namingpaper.models import PaperMetadata


class TestSanitizeFilename:
    def test_removes_invalid_characters(self):
        assert sanitize_filename('file<>:"/\\|?*name') == "filename"

    def test_normalizes_whitespace(self):
        assert sanitize_filename("file   name") == "file name"
        assert sanitize_filename("file___name") == "file name"

    def test_strips_dots_and_spaces(self):
        assert sanitize_filename("  .filename.  ") == "filename"

    def test_handles_unicode(self):
        # Should normalize unicode
        result = sanitize_filename("café")
        assert "caf" in result


class TestFormatAuthors:
    def test_single_author(self):
        assert format_authors(["Smith"]) == "Smith"

    def test_two_authors(self):
        assert format_authors(["Smith", "Jones"]) == "Smith, Jones"

    def test_three_authors(self):
        assert format_authors(["Smith", "Jones", "Brown"]) == "Smith, Jones, Brown"

    def test_four_authors_uses_et_al(self):
        assert format_authors(["Smith", "Jones", "Brown", "Davis"]) == "Smith et al"

    def test_empty_authors(self):
        assert format_authors([]) == "Unknown"

    def test_custom_max_authors(self):
        assert format_authors(["Smith", "Jones", "Brown"], max_authors=2) == "Smith et al"


class TestFormatJournal:
    def test_uses_abbreviation_if_available(self):
        assert format_journal("Journal of Finance", "JF") == "JF"

    def test_uses_full_name_if_no_abbrev(self):
        assert format_journal("Journal of Finance", None) == "Journal of Finance"


class TestFormatTitle:
    def test_short_title_unchanged(self):
        assert format_title("Short title") == "Short title"

    def test_long_title_truncated(self):
        result = format_title("One two three four five six seven eight nine ten")
        assert result == "One two three four five six..."

    def test_custom_max_words(self):
        result = format_title("One two three four five", max_words=3)
        assert result == "One two three..."


class TestBuildFilename:
    def test_standard_format(self, sample_metadata: PaperMetadata):
        filename = build_filename(sample_metadata)
        assert filename == "Fama, French, (1993, JFE), Common risk factors in the returns....pdf"

    def test_many_authors_uses_et_al(self, sample_metadata_many_authors: PaperMetadata):
        filename = build_filename(sample_metadata_many_authors)
        assert filename.startswith("Smith et al, ")
        assert "(2020, AER)" in filename

    def test_no_journal_abbrev(self):
        metadata = PaperMetadata(
            authors=["Smith"],
            year=2020,
            journal="Some Journal",
            journal_abbrev=None,
            title="Title",
            confidence=0.9,
        )
        filename = build_filename(metadata)
        assert "(2020, Some Journal)" in filename

    def test_max_length_enforced(self, sample_metadata: PaperMetadata):
        filename = build_filename(sample_metadata, max_filename_length=50)
        assert len(filename) <= 50
        assert filename.endswith(".pdf")
