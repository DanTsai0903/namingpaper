"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from namingpaper.cli import app
from namingpaper.models import LowConfidenceError, PaperMetadata, RenameOperation


runner = CliRunner()


@pytest.fixture
def mock_plan_rename(sample_metadata: PaperMetadata, tmp_path: Path):
    """Mock the plan_rename_sync function."""
    source = tmp_path / "test.pdf"
    source.write_text("PDF content")

    operation = RenameOperation(
        source=source,
        destination=tmp_path / "Fama, French_(1993, JFE)_Common risk factors.pdf",
        metadata=sample_metadata,
    )

    with patch("namingpaper.cli.plan_rename_sync", return_value=operation) as mock:
        mock.source_path = source
        yield mock


class TestRenameCommand:
    def test_dry_run_shows_metadata(self, mock_plan_rename, tmp_path: Path):
        source = mock_plan_rename.source_path
        result = runner.invoke(app, ["rename", str(source)])

        assert result.exit_code == 0
        assert "Fama" in result.output
        assert "French" in result.output
        assert "1993" in result.output
        assert "JFE" in result.output
        assert "Dry run mode" in result.output

    def test_execute_with_confirmation(self, mock_plan_rename, tmp_path: Path):
        source = mock_plan_rename.source_path

        with patch("namingpaper.cli.execute_rename") as mock_exec:
            mock_exec.return_value = tmp_path / "renamed.pdf"
            result = runner.invoke(app, ["rename", str(source), "--execute", "--yes"])

        assert result.exit_code == 0
        mock_exec.assert_called_once()

    def test_non_pdf_rejected(self, tmp_path: Path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")

        result = runner.invoke(app, ["rename", str(txt_file)])

        assert result.exit_code == 1
        assert "must be a PDF" in result.output

    def test_file_not_found(self, tmp_path: Path):
        result = runner.invoke(app, ["rename", str(tmp_path / "nonexistent.pdf")])
        assert result.exit_code != 0


    def test_low_confidence_skipped(self, tmp_path: Path):
        source = tmp_path / "invoice.pdf"
        source.write_text("PDF content")

        with patch(
            "namingpaper.cli.plan_rename_sync",
            side_effect=LowConfidenceError(0.1, 0.5),
        ):
            result = runner.invoke(app, ["rename", str(source)])

        assert result.exit_code == 2
        assert "Skipped" in result.output
        assert "academic paper" in result.output


class TestConfigCommand:
    def test_config_show(self):
        with patch("namingpaper.cli.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="claude",
                anthropic_api_key="sk-test1234",
                openai_api_key=None,
                gemini_api_key=None,
                ollama_base_url="http://localhost:11434",
                ollama_ocr_model=None,
                max_authors=3,
                max_filename_length=200,
            )
            result = runner.invoke(app, ["config", "--show"])

        assert result.exit_code == 0
        assert "claude" in result.output
        assert "set" in result.output  # Key status shown without revealing characters
        assert "localhost:11434" in result.output  # Ollama URL

    def test_config_no_args(self):
        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert "Environment variables" in result.output


class TestTemplatesCommand:
    def test_shows_all_presets(self):
        result = runner.invoke(app, ["templates"])

        assert result.exit_code == 0
        assert "default" in result.output
        assert "compact" in result.output
        assert "full" in result.output
        assert "simple" in result.output

    def test_shows_patterns(self):
        result = runner.invoke(app, ["templates"])

        assert result.exit_code == 0
        assert "{authors}" in result.output
        assert "{year}" in result.output

    def test_shows_usage_hint(self):
        result = runner.invoke(app, ["templates"])

        assert result.exit_code == 0
        assert "--template" in result.output


class TestCheckCommand:
    def test_check_cloud_provider_missing_key(self):
        with patch("namingpaper.cli.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="claude",
                anthropic_api_key=None,
                ollama_base_url="http://localhost:11434",
                ollama_ocr_model=None,
                model_name=None,
            )
            result = runner.invoke(app, ["check", "--provider", "claude"])

        assert result.exit_code == 1
        assert "MISSING" in result.output

    def test_check_cloud_provider_with_key(self):
        with patch("namingpaper.cli.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="claude",
                anthropic_api_key="sk-test",
                ollama_base_url="http://localhost:11434",
                ollama_ocr_model=None,
                model_name=None,
            )
            result = runner.invoke(app, ["check", "--provider", "claude"])

        assert result.exit_code == 0
        assert "All checks passed" in result.output

    def test_check_unknown_provider(self):
        with patch("namingpaper.cli.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="unknown_provider",
                ollama_base_url="http://localhost:11434",
                ollama_ocr_model=None,
                model_name=None,
            )
            result = runner.invoke(app, ["check", "--provider", "unknown_provider"])

        assert result.exit_code == 1
        assert "UNKNOWN" in result.output
