"""
LLM Provider Registry

Central registry for all supported LLM providers with their capabilities.

Author: Luke Steuber
"""

from typing import Dict, List, Optional, Any, Type
from .base import BaseProvider


# Provider registry with capabilities
PROVIDERS: Dict[str, Dict[str, Any]] = {
    "gemini": {
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
        "text": True,
        "vision": True,
        "audio": True,
        "video": True,
        "image_gen": True,
        "tts": True,
        "embedding": True,
        "description": "Google Gemini - Most comprehensive multimodal capabilities",
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
        "text": True,
        "vision": True,
        "audio": True,  # Whisper
        "video": False,
        "image_gen": True,  # DALL-E
        "tts": True,
        "embedding": True,
        "description": "OpenAI - GPT models, DALL-E, Whisper, TTS",
    },
    "anthropic": {
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
        "text": True,
        "vision": True,
        "audio": False,
        "video": False,
        "image_gen": False,
        "tts": False,
        "embedding": False,
        "description": "Anthropic - Claude models with vision",
    },
    "xai": {
        "env_key": "XAI_API_KEY",
        "default_model": "grok-3",
        "text": True,
        "vision": True,
        "audio": False,
        "video": False,
        "image_gen": True,  # Aurora
        "tts": False,
        "embedding": False,
        "description": "xAI - Grok models with Aurora image gen",
    },
    "mistral": {
        "env_key": "MISTRAL_API_KEY",
        "default_model": "mistral-large-latest",
        "text": True,
        "vision": True,
        "audio": False,
        "video": False,
        "image_gen": False,
        "tts": False,
        "embedding": True,
        "description": "Mistral AI - Fast inference with vision",
    },
    "cohere": {
        "env_key": "COHERE_API_KEY",
        "default_model": "command-r-08-2024",
        "text": True,
        "vision": False,
        "audio": False,
        "video": False,
        "image_gen": False,
        "tts": False,
        "embedding": True,
        "description": "Cohere - Enterprise text and embeddings",
    },
    "perplexity": {
        "env_key": "PERPLEXITY_API_KEY",
        "default_model": "sonar-pro",
        "text": True,
        "vision": False,
        "audio": False,
        "video": False,
        "image_gen": False,
        "tts": False,
        "embedding": False,
        "description": "Perplexity - Web-grounded search AI",
    },
}


# Provider class registry (populated as providers are imported)
_provider_classes: Dict[str, Type[BaseProvider]] = {}


def register_provider(name: str, provider_class: Type[BaseProvider]) -> None:
    """Register a provider class."""
    _provider_classes[name] = provider_class


def get_provider(name: str) -> Optional[Type[BaseProvider]]:
    """Get a provider class by name."""
    return _provider_classes.get(name)


def get_available_providers() -> List[str]:
    """Get list of providers that have API keys configured."""
    import os
    available = []
    for name, info in PROVIDERS.items():
        env_key = info.get("env_key", f"{name.upper()}_API_KEY")
        if os.getenv(env_key):
            available.append(name)
    return available


def get_providers_with_capability(capability: str) -> List[str]:
    """Get list of providers that support a given capability."""
    return [name for name, info in PROVIDERS.items() if info.get(capability)]


def get_best_provider_for(capability: str) -> Optional[str]:
    """Get the best available provider for a capability."""
    available = get_available_providers()
    capable = get_providers_with_capability(capability)

    # Priority order for each capability
    priority = {
        "text": ["gemini", "openai", "anthropic", "xai", "mistral", "cohere", "perplexity"],
        "vision": ["gemini", "openai", "anthropic", "xai", "mistral"],
        "audio": ["gemini", "openai"],
        "video": ["gemini"],
        "image_gen": ["openai", "xai", "gemini"],
        "tts": ["openai", "gemini"],
        "embedding": ["openai", "gemini", "cohere", "mistral"],
    }

    for provider in priority.get(capability, list(PROVIDERS.keys())):
        if provider in available and provider in capable:
            return provider

    return None


__all__ = [
    "PROVIDERS",
    "register_provider",
    "get_provider",
    "get_available_providers",
    "get_providers_with_capability",
    "get_best_provider_for",
    "BaseProvider",
]
