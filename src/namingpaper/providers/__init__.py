"""AI provider registry."""

from typing import TYPE_CHECKING

from namingpaper.config import get_settings

if TYPE_CHECKING:
    from namingpaper.providers.base import AIProvider


def get_provider(provider_name: str | None = None) -> "AIProvider":
    """Get an AI provider instance by name.

    Args:
        provider_name: Provider name ("claude", "openai", "gemini", "ollama").
                      If None, uses the configured default.

    Returns:
        An initialized AIProvider instance.

    Raises:
        ValueError: If provider is not supported or not installed.
    """
    settings = get_settings()
    name = provider_name or settings.ai_provider

    match name:
        case "claude":
            from namingpaper.providers.claude import ClaudeProvider

            if not settings.anthropic_api_key:
                raise ValueError(
                    "NAMINGPAPER_ANTHROPIC_API_KEY environment variable not set"
                )
            return ClaudeProvider(
                api_key=settings.anthropic_api_key,
                model=settings.model_name,
            )
        case "openai":
            try:
                from namingpaper.providers.openai import OpenAIProvider
            except ImportError:
                raise ValueError(
                    "OpenAI provider not installed. Run: pip install namingpaper[openai]"
                )
            if not settings.openai_api_key:
                raise ValueError(
                    "NAMINGPAPER_OPENAI_API_KEY environment variable not set"
                )
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.model_name,
            )
        case "gemini":
            try:
                from namingpaper.providers.gemini import GeminiProvider
            except ImportError:
                raise ValueError(
                    "Gemini provider not installed. Run: pip install namingpaper[gemini]"
                )
            if not settings.gemini_api_key:
                raise ValueError(
                    "NAMINGPAPER_GEMINI_API_KEY environment variable not set"
                )
            return GeminiProvider(
                api_key=settings.gemini_api_key,
                model=settings.model_name,
            )
        case "ollama":
            from namingpaper.providers.ollama import OllamaProvider

            return OllamaProvider(
                model=settings.model_name,
                base_url=settings.ollama_base_url,
            )
        case _:
            raise ValueError(f"Unknown provider: {name}")
