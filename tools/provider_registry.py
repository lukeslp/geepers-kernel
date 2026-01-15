"""
Provider Tool Registration Utilities

Convenience helpers to register all provider-backed ToolModuleBase implementations
with the global ToolRegistry. Handles missing API keys and optional dependencies
gracefully so consumers can inspect which tools are available at runtime.
"""

from importlib import import_module
from typing import Any, Dict, List, Optional, Tuple

from .registry import get_registry, ToolRegistry
from .module_base import ToolModuleBase

# (module_path, class_name)
PROVIDER_TOOL_CLASSES: List[Tuple[str, str]] = [
    ("shared.tools.openai_tools", "OpenAITools"),
    ("shared.tools.anthropic_tools", "AnthropicTools"),
    ("shared.tools.xai_tools", "XAITools"),
    ("shared.tools.mistral_tools", "MistralTools"),
    ("shared.tools.cohere_tools", "CohereTools"),
    ("shared.tools.gemini_tools", "GeminiTools"),
    ("shared.tools.perplexity_tools", "PerplexityTools"),
    ("shared.tools.groq_tools", "GroqTools"),
    ("shared.tools.huggingface_tools", "HuggingFaceTools"),
    ("shared.tools.elevenlabs_tools", "ElevenLabsTools"),
]


def register_provider_tools(
    config: Optional[Dict[str, Dict[str, Any]]] = None,
    registry: Optional[ToolRegistry] = None,
    skip_errors: bool = True
) -> Dict[str, Any]:
    """
    Register all provider tool modules with the ToolRegistry.

    Args:
        config: Optional per-provider configuration (e.g., API keys). Keys should
            match the tool module's `name` attribute (e.g., "openai").
        registry: Optional registry instance. Defaults to global registry.
        skip_errors: If False, raises on first registration failure.

    Returns:
        Dictionary with lists of successfully registered provider names and any
        errors keyed by provider.
    """
    config = config or {}
    registry = registry or get_registry()

    registered: List[str] = []
    errors: Dict[str, str] = {}

    for module_path, class_name in PROVIDER_TOOL_CLASSES:
        provider_key = module_path.rsplit(".", 1)[-1].replace("_tools", "")

        try:
            module = import_module(module_path)
            tool_cls = getattr(module, class_name)
            if not issubclass(tool_cls, ToolModuleBase):
                raise TypeError(f"{class_name} is not a ToolModuleBase subclass")

            tool_config = config.get(tool_cls.name, {})
            tool_instance = tool_cls(tool_config)
            result = tool_instance.register_with_registry(registry=registry)

            if result.get("success"):
                registered.append(tool_instance.name)
            else:
                errors[tool_instance.name] = result.get("error", "Unknown registration error")
                if not skip_errors:
                    raise RuntimeError(errors[tool_instance.name])

        except Exception as exc:  # noqa: BLE001 - we want to capture any provider failure
            errors[provider_key] = str(exc)
            if not skip_errors:
                raise

    return {"registered": registered, "errors": errors}


__all__ = ["register_provider_tools", "PROVIDER_TOOL_CLASSES"]

