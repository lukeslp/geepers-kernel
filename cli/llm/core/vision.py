"""
Unified vision command.

Auto-selects the best available vision-capable provider.

Author: Luke Steuber
"""

from pathlib import Path
from typing import Optional

from rich.console import Console

from ..config import get_config
from ..providers import get_best_provider_for, get_available_providers, PROVIDERS
from ..utils import print_error, print_response, print_json, is_image

console = Console()


def unified_vision(
    image: Path,
    prompt: str = "Describe this image in detail",
    provider: str = "auto",
    model: Optional[str] = None,
    json_output: bool = False,
):
    """
    Analyze an image with auto-provider selection.

    Args:
        image: Path to image file
        prompt: Analysis prompt
        provider: Provider name or "auto"
        model: Specific model
        json_output: Output as JSON
    """
    # Validate image exists
    if not image.exists():
        print_error(f"Image not found: {image}")
        return

    if not is_image(image):
        print_error(
            f"Not a supported image format: {image.suffix}",
            "Supported: PNG, JPEG, WEBP, HEIC, HEIF, GIF, BMP, TIFF"
        )
        return

    # Select provider
    if provider == "auto":
        provider = get_best_provider_for("vision")
        if not provider:
            print_error(
                "No vision-capable providers available",
                "Set an API key for Gemini, OpenAI, Anthropic, xAI, or Mistral"
            )
            return

    # Validate provider has vision capability
    if provider not in PROVIDERS:
        print_error(f"Unknown provider: {provider}")
        return

    if not PROVIDERS[provider].get("vision"):
        print_error(f"Provider '{provider}' does not support vision")
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
    use_model = model or config.get_provider_model(provider)

    # Execute vision analysis
    try:
        provider_instance = _get_vision_provider(provider, use_model)
        response = provider_instance.analyze_image(
            image=image,
            prompt=prompt,
            model=use_model,
        )

        if json_output:
            print_json({
                "content": response.content,
                "model": response.model,
                "usage": response.usage,
                "provider": provider,
                "image": str(image),
            })
        else:
            print_response(response.content, title=f"Vision Analysis ({provider})")

    except Exception as e:
        print_error(f"Vision analysis failed: {e}")


def _get_vision_provider(provider: str, model: str):
    """Get a vision-capable provider instance."""
    if provider == "gemini":
        from ..providers.gemini.client import GeminiProvider
        return GeminiProvider(model=model)
    elif provider == "openai":
        from ..providers.openai.client import OpenAIProvider
        return OpenAIProvider(model=model)
    elif provider == "anthropic":
        from ..providers.anthropic.client import AnthropicProvider
        return AnthropicProvider(model=model)
    elif provider == "xai":
        from ..providers.xai.client import XAIProvider
        return XAIProvider(model=model)
    elif provider == "mistral":
        from ..providers.mistral.client import MistralProvider
        return MistralProvider(model=model)
    else:
        raise ValueError(f"Provider '{provider}' does not support vision")
