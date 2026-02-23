"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from namingpaper.cli import app
from namingpaper import __version__
from namingpaper.models import LowConfidenceError, PaperMetadata, RenameOperation


runner = CliRunner()


class TestVersionCommand:
    def test_version(self):
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert f"namingpaper {__version__}" in result.output

    def test_version_short_flag(self):
        result = runner.invoke(app, ["-v"])

        assert result.exit_code == 0
        assert f"namingpaper {__version__}" in result.output


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
        import sys
        with patch("namingpaper.cli.get_settings") as mock_settings, \
             patch.dict(sys.modules, {"anthropic": MagicMock()}):
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


class TestUninstallCommand:
    def test_uninstall_auto_detects_uv(self):
        with patch("namingpaper.cli.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/uv" if cmd == "uv" else None
            result = runner.invoke(app, ["uninstall"])

        assert result.exit_code == 0
        assert "Detected manager" in result.output
        assert "uv" in result.output
        assert "uv tool uninstall namingpaper" in result.output

    def test_uninstall_explicit_pipx(self):
        result = runner.invoke(app, ["uninstall", "--manager", "pipx"])

        assert result.exit_code == 0
        assert "pipx uninstall namingpaper" in result.output

    def test_uninstall_execute_with_yes_uses_pip_y_flag(self):
        process_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("namingpaper.cli.subprocess.run", return_value=process_result) as mock_run:
            result = runner.invoke(app, ["uninstall", "--manager", "pip", "--execute", "--yes"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[2:6] == ["pip", "uninstall", "-y", "namingpaper"]

    def test_uninstall_execute_with_purge_removes_user_dir(self, tmp_path: Path):
        process_result = MagicMock(returncode=0, stdout="ok", stderr="")
        config_dir = tmp_path / ".namingpaper"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text("ai_provider = 'ollama'")

        with patch("namingpaper.cli.subprocess.run", return_value=process_result), \
             patch("namingpaper.cli.Path.home", return_value=tmp_path):
            result = runner.invoke(
                app,
                ["uninstall", "--manager", "pip", "--execute", "--yes", "--purge"],
            )

        assert result.exit_code == 0
        assert not config_dir.exists()

    def test_uninstall_execute_with_purge_no_dir(self, tmp_path: Path):
        process_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("namingpaper.cli.subprocess.run", return_value=process_result), \
             patch("namingpaper.cli.Path.home", return_value=tmp_path):
            result = runner.invoke(
                app,
                ["uninstall", "--manager", "pip", "--execute", "--yes", "--purge"],
            )

        assert result.exit_code == 0
        assert "No user config/data directory found" in result.output
