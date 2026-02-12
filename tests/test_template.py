"""Tests for template module."""

import pytest

from namingpaper.models import PaperMetadata
from namingpaper.template import (
    get_template,
    validate_template,
    build_filename_from_template,
    list_presets,
    PRESET_TEMPLATES,
)


class TestGetTemplate:
    """Tests for get_template function."""

    def test_get_preset_template(self) -> None:
        """Should return preset template by name."""
        result = get_template("default")
        assert result == PRESET_TEMPLATES["default"]

    def test_get_custom_template(self) -> None:
        """Should return custom template string as-is."""
        custom = "{authors} - {year}"
        result = get_template(custom)
        assert result == custom

    def test_all_presets_exist(self) -> None:
        """All documented presets should be available."""
        for name in ["default", "compact", "full", "simple"]:
            assert name in PRESET_TEMPLATES


class TestValidateTemplate:
    """Tests for validate_template function."""

    def test_valid_template(self) -> None:
        """Should accept valid template."""
        is_valid, error = validate_template("{authors} ({year}) {title}")
        assert is_valid
        assert error is None

    def test_invalid_placeholder(self) -> None:
        """Should reject invalid placeholder."""
        is_valid, error = validate_template("{authors} {invalid}")
        assert not is_valid
        assert "invalid" in error.lower()

    def test_empty_template(self) -> None:
        """Should reject template without placeholders."""
        is_valid, error = validate_template("no placeholders here")
        assert not is_valid

    def test_all_valid_placeholders(self) -> None:
        """Should accept all valid placeholders."""
        template = "{authors} {year} {journal} {journal_abbrev} {journal_full} {title}"
        is_valid, error = validate_template(template)
        assert is_valid


class TestBuildFilenameFromTemplate:
    """Tests for build_filename_from_template function."""

    @pytest.fixture
    def metadata(self) -> PaperMetadata:
        return PaperMetadata(
            authors=["Fama", "French"],
            year=1993,
            journal="Journal of Financial Economics",
            journal_abbrev="JFE",
            title="Common risk factors in stock returns",
            confidence=0.95,
        )

    def test_default_template(self, metadata: PaperMetadata) -> None:
        """Should format using default template."""
        result = build_filename_from_template(metadata, "default")
        assert "Fama and French" in result
        assert "1993" in result
        assert "JFE" in result
        assert result.endswith(".pdf")

    def test_compact_template(self, metadata: PaperMetadata) -> None:
        """Should format using compact template."""
        result = build_filename_from_template(metadata, "compact")
        assert "Fama and French" in result
        assert "(1993)" in result
        assert "JFE" not in result  # compact doesn't include journal
        assert result.endswith(".pdf")

    def test_simple_template(self, metadata: PaperMetadata) -> None:
        """Should format using simple template with dash separators."""
        result = build_filename_from_template(metadata, "simple")
        assert "1993" in result
        assert " - " in result
        assert result.endswith(".pdf")

    def test_custom_template(self, metadata: PaperMetadata) -> None:
        """Should format using custom template."""
        result = build_filename_from_template(metadata, "{year} - {authors}")
        assert result.startswith("1993 - Fama")
        assert result.endswith(".pdf")

    def test_journal_full_placeholder(self, metadata: PaperMetadata) -> None:
        """Should use full journal name with journal_full placeholder."""
        result = build_filename_from_template(metadata, "{journal_full}")
        assert "Journal of Financial Economics" in result

    def test_journal_abbrev_placeholder(self, metadata: PaperMetadata) -> None:
        """Should use abbreviation with journal_abbrev placeholder."""
        result = build_filename_from_template(metadata, "{journal_abbrev}")
        assert "JFE" in result

    def test_max_filename_length(self, metadata: PaperMetadata) -> None:
        """Should truncate filename if too long."""
        result = build_filename_from_template(
            metadata,
            "{authors} {title} {title} {title}",
            max_filename_length=50,
        )
        assert len(result) <= 50
        assert result.endswith(".pdf")

    def test_adds_pdf_extension(self, metadata: PaperMetadata) -> None:
        """Should add .pdf extension if not present."""
        result = build_filename_from_template(metadata, "{year}")
        assert result == "1993.pdf"

    def test_many_authors_truncation(self) -> None:
        """Should truncate to 'et al' with many authors."""
        metadata = PaperMetadata(
            authors=["Smith", "Jones", "Brown", "Davis"],
            year=2020,
            journal="Test Journal",
            title="Test Title",
        )
        result = build_filename_from_template(metadata, "{authors}", max_authors=3)
        assert "et al" in result


class TestListPresets:
    """Tests for list_presets function."""

    def test_returns_all_presets(self) -> None:
        """Should return all preset templates."""
        presets = list_presets()
        assert "default" in presets
        assert "compact" in presets
        assert "full" in presets
        assert "simple" in presets

    def test_returns_copy(self) -> None:
        """Should return a copy, not the original dict."""
        presets = list_presets()
        presets["modified"] = "test"
        assert "modified" not in PRESET_TEMPLATES
