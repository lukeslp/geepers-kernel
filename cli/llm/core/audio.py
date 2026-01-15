"""
Unified audio command.

Auto-selects the best available audio-capable provider.

Author: Luke Steuber
"""

from pathlib import Path
from typing import Optional

from rich.console import Console

from ..config import get_config
from ..providers import get_best_provider_for, get_available_providers, PROVIDERS
from ..utils import print_error, print_response, print_json, is_audio

console = Console()


def unified_audio(
    file: Path,
    prompt: str = "Transcribe this audio",
    provider: str = "auto",
    json_output: bool = False,
):
    """
    Process audio with auto-provider selection.

    Args:
        file: Path to audio file
        prompt: Processing prompt
        provider: Provider name or "auto"
        json_output: Output as JSON
    """
    # Validate audio exists
    if not file.exists():
        print_error(f"Audio file not found: {file}")
        return

    if not is_audio(file):
        print_error(
            f"Not a supported audio format: {file.suffix}",
            "Supported: MP3, WAV, AIFF, AAC, OGG, FLAC, M4A"
        )
        return

    # Select provider
    if provider == "auto":
        provider = get_best_provider_for("audio")
        if not provider:
            print_error(
                "No audio-capable providers available",
                "Set an API key for Gemini or OpenAI"
            )
            return

    # Validate provider has audio capability
    if provider not in PROVIDERS:
        print_error(f"Unknown provider: {provider}")
        return

    if not PROVIDERS[provider].get("audio"):
        print_error(f"Provider '{provider}' does not support audio")
        return

    available = get_available_providers()
    if provider not in available:
        print_error(
            f"Provider '{provider}' not configured",
            f"Set {PROVIDERS[provider]['env_key']} environment variable"
        )
        return

    # Get model
    config = get_config()
    use_model = config.get_provider_model(provider)

    # Execute audio processing
    try:
        provider_instance = _get_audio_provider(provider, use_model)
        response = provider_instance.analyze_audio(
            audio=file,
            prompt=prompt,
        )

        if json_output:
            print_json({
                "content": response.content,
                "model": response.model,
                "usage": response.usage,
                "provider": provider,
                "audio_file": str(file),
            })
        else:
            print_response(response.content, title=f"Audio Analysis ({provider})")

    except Exception as e:
        print_error(f"Audio processing failed: {e}")


def _get_audio_provider(provider: str, model: str):
    """Get an audio-capable provider instance."""
    if provider == "gemini":
        from ..providers.gemini.client import GeminiProvider
        return GeminiProvider(model=model)
    elif provider == "openai":
        from ..providers.openai.client import OpenAIProvider
        return OpenAIProvider(model=model)
    else:
        raise ValueError(f"Provider '{provider}' does not support audio")
