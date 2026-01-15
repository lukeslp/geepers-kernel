"""
Configuration management for LLM CLI.

Handles API keys, default providers, and user preferences.

Author: Luke Steuber
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


# Environment variable mappings for each provider
ENV_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
}

# Default models for each provider
DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "xai": "grok-3",
    "mistral": "mistral-large-latest",
    "cohere": "command-r-plus",
    "perplexity": "sonar-pro",
}


@dataclass
class Config:
    """Configuration for LLM CLI."""

    default_provider: str = "gemini"
    config_path: Path = field(default_factory=lambda: Path.home() / ".llm" / "config.json")
    provider_models: Dict[str, str] = field(default_factory=dict)
    provider_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Load configuration from file if it exists."""
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                    self.default_provider = data.get("default_provider", self.default_provider)
                    self.provider_models = data.get("provider_models", {})
                    self.provider_settings = data.get("provider_settings", {})
            except (json.JSONDecodeError, IOError):
                pass

    def save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump({
                "default_provider": self.default_provider,
                "provider_models": self.provider_models,
                "provider_settings": self.provider_settings,
            }, f, indent=2)

    def has_api_key(self, provider: str) -> bool:
        """Check if API key exists for provider."""
        env_key = ENV_KEYS.get(provider, f"{provider.upper()}_API_KEY")
        return bool(os.getenv(env_key))

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider."""
        env_key = ENV_KEYS.get(provider, f"{provider.upper()}_API_KEY")
        return os.getenv(env_key)

    def get_provider_model(self, provider: str) -> str:
        """Get configured model for provider, or default."""
        return self.provider_models.get(provider, DEFAULT_MODELS.get(provider, ""))

    def set_provider_model(self, provider: str, model: str) -> None:
        """Set model for provider."""
        self.provider_models[provider] = model
        self.save()

    def get_provider_setting(self, provider: str, key: str, default: Any = None) -> Any:
        """Get a provider-specific setting."""
        return self.provider_settings.get(provider, {}).get(key, default)

    def set_provider_setting(self, provider: str, key: str, value: Any) -> None:
        """Set a provider-specific setting."""
        if provider not in self.provider_settings:
            self.provider_settings[provider] = {}
        self.provider_settings[provider][key] = value
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key (dot notation supported)."""
        parts = key.split(".")
        if len(parts) == 1:
            return getattr(self, key, default)
        elif len(parts) == 2:
            provider, setting = parts
            if setting == "model":
                return self.get_provider_model(provider)
            return self.get_provider_setting(provider, setting, default)
        return default

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by key (dot notation supported)."""
        parts = key.split(".")
        if len(parts) == 1:
            if hasattr(self, key):
                setattr(self, key, value)
                self.save()
        elif len(parts) == 2:
            provider, setting = parts
            if setting == "model":
                self.set_provider_model(provider, value)
            else:
                self.set_provider_setting(provider, setting, value)


# Singleton config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset the global configuration (for testing)."""
    global _config
    _config = None
