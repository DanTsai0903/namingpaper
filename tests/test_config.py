"""Tests for configuration management."""

import pytest

from namingpaper.config import Settings, get_settings, reset_settings


class TestSettings:
    def test_default_values(self):
        settings = Settings()
        assert settings.ai_provider == "ollama"
        assert settings.max_authors == 3
        assert settings.max_filename_length == 200
        assert settings.max_text_chars == 8000
        assert settings.min_confidence == 0.5
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.anthropic_api_key is None
        assert settings.openai_api_key is None
        assert settings.gemini_api_key is None
        assert settings.model_name is None
        assert settings.ollama_ocr_model is None

    def test_custom_values(self):
        settings = Settings(
            ai_provider="claude",
            max_authors=5,
            max_filename_length=150,
        )
        assert settings.ai_provider == "claude"
        assert settings.max_authors == 5
        assert settings.max_filename_length == 150

    def test_invalid_provider_rejected(self):
        with pytest.raises(Exception):
            Settings(ai_provider="invalid")

    def test_max_authors_minimum(self):
        with pytest.raises(Exception):
            Settings(max_authors=0)

    def test_max_filename_length_bounds(self):
        with pytest.raises(Exception):
            Settings(max_filename_length=10)
        with pytest.raises(Exception):
            Settings(max_filename_length=300)

    def test_min_confidence_bounds(self):
        with pytest.raises(Exception):
            Settings(min_confidence=-0.1)
        with pytest.raises(Exception):
            Settings(min_confidence=1.5)

    def test_extra_fields_ignored(self):
        settings = Settings(unknown_field="value")
        assert not hasattr(settings, "unknown_field")

    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv("NAMINGPAPER_AI_PROVIDER", "claude")
        monkeypatch.setenv("NAMINGPAPER_ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("NAMINGPAPER_MAX_AUTHORS", "5")
        settings = Settings()
        assert settings.ai_provider == "claude"
        assert settings.anthropic_api_key == "test-key"
        assert settings.max_authors == 5

    def test_load_from_config_file(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".namingpaper"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('ai_provider = "claude"\nmax_authors = 5\n')
        monkeypatch.setattr("namingpaper.config.Path.home", lambda: tmp_path)
        settings = Settings.load()
        assert settings.ai_provider == "claude"
        assert settings.max_authors == 5

    def test_load_invalid_toml(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".namingpaper"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text("invalid toml [[[")
        monkeypatch.setattr("namingpaper.config.Path.home", lambda: tmp_path)
        with pytest.raises(ValueError, match="Invalid TOML"):
            Settings.load()

    def test_load_no_config_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("namingpaper.config.Path.home", lambda: tmp_path)
        settings = Settings.load()
        assert settings.ai_provider == "ollama"


class TestGetSettings:
    def test_returns_settings_instance(self):
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_caches_settings(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reset_clears_cache(self):
        s1 = get_settings()
        reset_settings()
        s2 = get_settings()
        assert s1 is not s2
