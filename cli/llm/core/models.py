"""
Model listing and information commands.

Shows available models across all configured providers.

Author: Luke Steuber
"""

from typing import Optional, Dict, Any, List

from rich.console import Console
from rich.table import Table

from ..config import get_config
from ..providers import PROVIDERS, get_available_providers
from ..utils import print_error, print_json

console = Console()

# Default models for each provider (comprehensive list)
PROVIDER_MODELS: Dict[str, Dict[str, Any]] = {
    "gemini": {
        "text": [
            {"name": "gemini-2.5-flash", "description": "Fast, efficient model", "context": "1M"},
            {"name": "gemini-2.5-pro", "description": "Advanced reasoning", "context": "1M"},
            {"name": "gemini-3-flash-preview", "description": "Next-gen fast model", "context": "1M"},
            {"name": "gemini-3-pro-preview", "description": "Next-gen advanced model", "context": "1M"},
        ],
        "vision": [
            {"name": "gemini-2.5-flash", "description": "Multimodal vision", "context": "1M"},
            {"name": "gemini-2.5-pro", "description": "Advanced vision analysis", "context": "1M"},
        ],
        "audio": [
            {"name": "gemini-2.5-flash", "description": "Audio transcription & analysis", "context": "1M"},
        ],
        "video": [
            {"name": "gemini-2.5-flash", "description": "Video analysis (up to 6hr)", "context": "1M"},
        ],
        "image_gen": [
            {"name": "imagen-4.0-generate-001", "description": "High-quality image generation"},
        ],
        "tts": [
            {"name": "gemini-2.5-flash-preview-tts", "description": "Text-to-speech"},
        ],
        "embedding": [
            {"name": "text-embedding-004", "description": "Text embeddings", "dimensions": 768},
        ],
    },
    "openai": {
        "text": [
            {"name": "gpt-4o", "description": "Latest GPT-4 Omni", "context": "128K"},
            {"name": "gpt-4o-mini", "description": "Fast, affordable GPT-4", "context": "128K"},
            {"name": "gpt-4-turbo", "description": "GPT-4 Turbo", "context": "128K"},
            {"name": "o1", "description": "Advanced reasoning model", "context": "128K"},
            {"name": "o1-mini", "description": "Fast reasoning model", "context": "128K"},
        ],
        "vision": [
            {"name": "gpt-4o", "description": "Vision with GPT-4 Omni", "context": "128K"},
            {"name": "gpt-4o-mini", "description": "Fast vision", "context": "128K"},
        ],
        "audio": [
            {"name": "whisper-1", "description": "Audio transcription"},
        ],
        "image_gen": [
            {"name": "dall-e-3", "description": "DALL-E 3 image generation"},
            {"name": "dall-e-2", "description": "DALL-E 2 image generation"},
        ],
        "tts": [
            {"name": "tts-1", "description": "Standard TTS"},
            {"name": "tts-1-hd", "description": "High-quality TTS"},
        ],
        "embedding": [
            {"name": "text-embedding-3-large", "description": "Best quality", "dimensions": 3072},
            {"name": "text-embedding-3-small", "description": "Efficient", "dimensions": 1536},
            {"name": "text-embedding-ada-002", "description": "Legacy", "dimensions": 1536},
        ],
    },
    "anthropic": {
        "text": [
            {"name": "claude-sonnet-4-20250514", "description": "Latest Claude Sonnet", "context": "200K"},
            {"name": "claude-opus-4-20250514", "description": "Most capable Claude", "context": "200K"},
            {"name": "claude-3-5-sonnet-20241022", "description": "Claude 3.5 Sonnet", "context": "200K"},
            {"name": "claude-3-5-haiku-20241022", "description": "Fast Claude 3.5", "context": "200K"},
        ],
        "vision": [
            {"name": "claude-sonnet-4-20250514", "description": "Vision with Sonnet 4", "context": "200K"},
            {"name": "claude-opus-4-20250514", "description": "Vision with Opus 4", "context": "200K"},
        ],
    },
    "xai": {
        "text": [
            {"name": "grok-3", "description": "Latest Grok model", "context": "128K"},
            {"name": "grok-3-fast", "description": "Fast Grok model", "context": "128K"},
            {"name": "grok-2", "description": "Grok 2", "context": "128K"},
        ],
        "vision": [
            {"name": "grok-2-vision", "description": "Grok vision model", "context": "128K"},
        ],
        "image_gen": [
            {"name": "aurora", "description": "Aurora image generation"},
        ],
    },
    "mistral": {
        "text": [
            {"name": "mistral-large-latest", "description": "Most capable Mistral", "context": "128K"},
            {"name": "mistral-medium-latest", "description": "Balanced performance", "context": "32K"},
            {"name": "mistral-small-latest", "description": "Fast and efficient", "context": "32K"},
            {"name": "codestral-latest", "description": "Code specialized", "context": "32K"},
        ],
        "vision": [
            {"name": "pixtral-large-latest", "description": "Vision model", "context": "128K"},
        ],
        "embedding": [
            {"name": "mistral-embed", "description": "Text embeddings", "dimensions": 1024},
        ],
    },
    "cohere": {
        "text": [
            {"name": "command-r-plus", "description": "Most capable", "context": "128K"},
            {"name": "command-r", "description": "Balanced", "context": "128K"},
            {"name": "command-light", "description": "Fast", "context": "4K"},
        ],
        "embedding": [
            {"name": "embed-english-v3.0", "description": "English embeddings", "dimensions": 1024},
            {"name": "embed-multilingual-v3.0", "description": "Multilingual", "dimensions": 1024},
        ],
    },
    "perplexity": {
        "text": [
            {"name": "sonar-pro", "description": "Advanced with citations", "context": "200K"},
            {"name": "sonar", "description": "Standard with citations", "context": "128K"},
            {"name": "sonar-reasoning-pro", "description": "Advanced reasoning", "context": "128K"},
            {"name": "sonar-reasoning", "description": "Standard reasoning", "context": "128K"},
        ],
    },
}


def list_models(
    provider: Optional[str] = None,
    capability: Optional[str] = None,
    json_output: bool = False,
):
    """
    List available models.

    Args:
        provider: Filter by specific provider
        capability: Filter by capability (text, vision, audio, etc.)
        json_output: Output as JSON
    """
    available = get_available_providers()

    if provider:
        if provider not in PROVIDERS:
            print_error(f"Unknown provider: {provider}")
            return
        if provider not in available:
            print_error(
                f"Provider '{provider}' not configured",
                f"Set {PROVIDERS[provider]['env_key']} environment variable"
            )
            return
        providers_to_show = [provider]
    else:
        providers_to_show = [p for p in PROVIDERS if p in available]

    if not providers_to_show:
        print_error(
            "No providers configured",
            "Set API keys for at least one provider"
        )
        return

    results = {}

    for prov in providers_to_show:
        if prov not in PROVIDER_MODELS:
            continue

        prov_models = PROVIDER_MODELS[prov]

        if capability:
            if capability in prov_models:
                results[prov] = {capability: prov_models[capability]}
        else:
            results[prov] = prov_models

    if json_output:
        print_json(results)
        return

    # Display as tables
    for prov, capabilities in results.items():
        console.print(f"\n[bold blue]{prov.upper()}[/bold blue]")
        console.print(f"[dim]API Key: {PROVIDERS[prov]['env_key']}[/dim]\n")

        for cap, models in capabilities.items():
            table = Table(title=f"{cap.replace('_', ' ').title()}")
            table.add_column("Model", style="cyan")
            table.add_column("Description")
            table.add_column("Details", style="dim")

            for model in models:
                details = []
                if "context" in model:
                    details.append(f"ctx:{model['context']}")
                if "dimensions" in model:
                    details.append(f"dim:{model['dimensions']}")

                table.add_row(
                    model["name"],
                    model.get("description", ""),
                    " ".join(details)
                )

            console.print(table)
            console.print()


def show_provider_status(json_output: bool = False):
    """
    Show status of all providers.

    Args:
        json_output: Output as JSON
    """
    available = get_available_providers()
    config = get_config()

    results = []

    for name, info in PROVIDERS.items():
        status = "configured" if name in available else "not configured"
        capabilities = [k for k, v in info.items() if k not in ["env_key", "default_model"] and v]

        result = {
            "provider": name,
            "status": status,
            "env_key": info["env_key"],
            "default_model": info["default_model"],
            "capabilities": capabilities,
            "configured_model": config.get_provider_model(name) if name in available else None,
        }
        results.append(result)

    if json_output:
        print_json(results)
        return

    # Display as table
    table = Table(title="LLM Provider Status")
    table.add_column("Provider", style="cyan")
    table.add_column("Status")
    table.add_column("Default Model")
    table.add_column("Capabilities", style="dim")

    for r in results:
        status_style = "green" if r["status"] == "configured" else "red"
        caps = ", ".join(r["capabilities"][:4])
        if len(r["capabilities"]) > 4:
            caps += f" +{len(r['capabilities']) - 4}"

        table.add_row(
            r["provider"],
            f"[{status_style}]{r['status']}[/{status_style}]",
            r["configured_model"] or r["default_model"],
            caps,
        )

    console.print(table)

    # Summary
    configured = len([r for r in results if r["status"] == "configured"])
    console.print(f"\n[dim]{configured}/{len(results)} providers configured[/dim]")


def get_model_info(model: str, provider: Optional[str] = None, json_output: bool = False):
    """
    Get information about a specific model.

    Args:
        model: Model name to look up
        provider: Optional provider hint
        json_output: Output as JSON
    """
    found = []

    search_providers = [provider] if provider else PROVIDER_MODELS.keys()

    for prov in search_providers:
        if prov not in PROVIDER_MODELS:
            continue

        for cap, models in PROVIDER_MODELS[prov].items():
            for m in models:
                if m["name"] == model or model in m["name"]:
                    found.append({
                        "provider": prov,
                        "capability": cap,
                        **m
                    })

    if not found:
        print_error(f"Model '{model}' not found")
        return

    if json_output:
        print_json(found)
        return

    for info in found:
        console.print(f"\n[bold]{info['name']}[/bold]")
        console.print(f"Provider: [cyan]{info['provider']}[/cyan]")
        console.print(f"Capability: {info['capability']}")
        if "description" in info:
            console.print(f"Description: {info['description']}")
        if "context" in info:
            console.print(f"Context Window: {info['context']}")
        if "dimensions" in info:
            console.print(f"Embedding Dimensions: {info['dimensions']}")
