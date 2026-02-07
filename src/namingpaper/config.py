"""Configuration management for namingpaper."""

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and config file."""

    model_config = SettingsConfigDict(
        env_prefix="NAMINGPAPER_",
        env_file=".env",
        extra="ignore",
    )

    # API keys
    anthropic_api_key: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)

    # Provider selection
    ai_provider: Literal["claude", "openai", "gemini", "ollama"] = Field(default="ollama")

    # Extraction settings
    model_name: str | None = Field(
        default=None, description="Override default model for provider"
    )
    max_text_chars: int = Field(
        default=8000, description="Max characters of text to send to AI"
    )

    # Ollama settings
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for Ollama API",
    )
    ollama_ocr_model: str | None = Field(
        default=None, description="Override OCR model for Ollama (default: deepseek-ocr)"
    )

    # Filename formatting
    max_authors: int = Field(
        default=3, description="Max authors before using 'et al'"
    )
    max_filename_length: int = Field(
        default=200, description="Maximum filename length"
    )

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment and config file."""
        config_path = Path.home() / ".namingpaper" / "config.toml"
        file_settings = {}

        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    file_settings = tomllib.load(f)
            except tomllib.TOMLDecodeError as e:
                raise ValueError(
                    f"Invalid TOML in config file '{config_path}': {e}"
                ) from e
            except PermissionError as e:
                raise ValueError(
                    f"Cannot read config file '{config_path}': permission denied"
                ) from e
            except OSError as e:
                raise ValueError(
                    f"Cannot read config file '{config_path}': {e}"
                ) from e

        return cls(**file_settings)


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings


def reset_settings() -> None:
    """Reset settings (useful for testing)."""
    global _settings
    _settings = None
