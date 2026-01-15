"""
Unified chat command.

Auto-selects the best available provider for text generation.

Author: Luke Steuber
"""

from typing import Optional
import json

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from ..config import get_config
from ..providers import get_best_provider_for, get_available_providers, PROVIDERS
from ..utils import print_error, print_response, print_json

console = Console()


def unified_chat(
    prompt: str,
    provider: str = "auto",
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = True,
    json_output: bool = False,
):
    """
    Execute a chat completion with auto-provider selection.

    Args:
        prompt: The user prompt
        provider: Provider name or "auto"
        model: Specific model (uses provider default if not specified)
        system: System prompt
        temperature: Sampling temperature
        max_tokens: Max tokens in response
        stream: Whether to stream the response
        json_output: Output as JSON instead of formatted text
    """
    # Select provider
    if provider == "auto":
        provider = get_best_provider_for("text")
        if not provider:
            print_error(
                "No text-capable providers available",
                "Set an API key for at least one provider (GEMINI_API_KEY, OPENAI_API_KEY, etc.)"
            )
            return

    # Validate provider
    if provider not in PROVIDERS:
        print_error(f"Unknown provider: {provider}")
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

    # Create provider instance and execute
    try:
        provider_instance = _get_provider_instance(provider, use_model)

        if stream and not json_output:
            _stream_chat(provider_instance, prompt, system, temperature, max_tokens)
        else:
            response = provider_instance.chat(
                messages=_build_messages(prompt, system),
                model=use_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if json_output:
                print_json({
                    "content": response.content,
                    "model": response.model,
                    "usage": response.usage,
                    "provider": provider,
                })
            else:
                print_response(response.content)

    except Exception as e:
        print_error(f"Chat failed: {e}")


def _get_provider_instance(provider: str, model: str):
    """Get a provider instance."""
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
    elif provider == "cohere":
        from ..providers.cohere.client import CohereProvider
        return CohereProvider(model=model)
    elif provider == "perplexity":
        from ..providers.perplexity.client import PerplexityProvider
        return PerplexityProvider(model=model)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _build_messages(prompt: str, system: Optional[str] = None):
    """Build message list from prompt and optional system message."""
    from ..providers.base import Message

    messages = []
    if system:
        messages.append(Message(role="system", content=system))
    messages.append(Message(role="user", content=prompt))
    return messages


def _stream_chat(provider, prompt: str, system: Optional[str], temperature: float, max_tokens: int):
    """Stream a chat response with live updating."""
    messages = _build_messages(prompt, system)

    full_response = ""
    with Live(Markdown(""), console=console, refresh_per_second=10) as live:
        for chunk in provider.chat_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            full_response += chunk
            live.update(Markdown(full_response))

    # Final newline
    console.print()
