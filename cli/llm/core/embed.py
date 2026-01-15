"""
Unified embedding command.

Auto-selects the best available provider for embeddings.

Author: Luke Steuber
"""

from typing import Optional, List
import json

from rich.console import Console

from ..config import get_config
from ..providers import get_best_provider_for, get_available_providers, PROVIDERS
from ..utils import print_error, print_response, print_json

console = Console()


def unified_embed(
    text: str,
    provider: str = "auto",
    model: Optional[str] = None,
    json_output: bool = False,
    output_file: Optional[str] = None,
):
    """
    Generate embeddings with auto-provider selection.

    Args:
        text: Text to embed
        provider: Provider name or "auto"
        model: Specific model
        json_output: Output as JSON
        output_file: Save embeddings to file
    """
    if not text.strip():
        print_error("Empty text provided", "Please provide text to embed")
        return

    # Select provider
    if provider == "auto":
        provider = get_best_provider_for("embedding")
        if not provider:
            print_error(
                "No embedding-capable providers available",
                "Set an API key for OpenAI, Gemini, Mistral, or Cohere"
            )
            return

    # Validate provider has embedding capability
    if provider not in PROVIDERS:
        print_error(f"Unknown provider: {provider}")
        return

    if not PROVIDERS[provider].get("embedding"):
        print_error(f"Provider '{provider}' does not support embeddings")
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

    # Execute embedding
    try:
        provider_instance = _get_embedding_provider(provider, use_model)
        response = provider_instance.embed(text=text)

        result = {
            "embedding": response.embedding,
            "model": response.model,
            "dimensions": len(response.embedding),
            "usage": response.usage,
            "provider": provider,
        }

        if output_file:
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            console.print(f"[green]Embeddings saved to {output_file}[/green]")
            console.print(f"Dimensions: {len(response.embedding)}")
        elif json_output:
            print_json(result)
        else:
            console.print(f"[bold]Embedding Generated ({provider})[/bold]")
            console.print(f"Model: {response.model}")
            console.print(f"Dimensions: {len(response.embedding)}")
            if response.usage:
                console.print(f"Tokens: {response.usage.get('total_tokens', 'N/A')}")
            console.print("\n[dim]First 10 values:[/dim]")
            console.print(response.embedding[:10])

    except Exception as e:
        print_error(f"Embedding failed: {e}")


def batch_embed(
    texts: List[str],
    provider: str = "auto",
    model: Optional[str] = None,
    json_output: bool = False,
    output_file: Optional[str] = None,
):
    """
    Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed
        provider: Provider name or "auto"
        model: Specific model
        json_output: Output as JSON
        output_file: Save embeddings to file
    """
    if not texts:
        print_error("No texts provided")
        return

    # Select provider
    if provider == "auto":
        provider = get_best_provider_for("embedding")
        if not provider:
            print_error(
                "No embedding-capable providers available",
                "Set an API key for OpenAI, Gemini, Mistral, or Cohere"
            )
            return

    # Validate provider
    if provider not in PROVIDERS:
        print_error(f"Unknown provider: {provider}")
        return

    if not PROVIDERS[provider].get("embedding"):
        print_error(f"Provider '{provider}' does not support embeddings")
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

    # Execute batch embedding
    try:
        provider_instance = _get_embedding_provider(provider, use_model)

        # Some providers support batch embedding natively
        if hasattr(provider_instance, 'embed_batch'):
            responses = provider_instance.embed_batch(texts=texts)
        else:
            # Fall back to sequential embedding
            responses = [provider_instance.embed(text=t) for t in texts]

        results = {
            "embeddings": [
                {
                    "text": texts[i][:50] + "..." if len(texts[i]) > 50 else texts[i],
                    "embedding": r.embedding,
                    "dimensions": len(r.embedding),
                }
                for i, r in enumerate(responses)
            ],
            "model": responses[0].model if responses else use_model,
            "count": len(responses),
            "provider": provider,
        }

        if output_file:
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            console.print(f"[green]Embeddings saved to {output_file}[/green]")
            console.print(f"Count: {len(responses)}")
        elif json_output:
            print_json(results)
        else:
            console.print(f"[bold]Batch Embeddings Generated ({provider})[/bold]")
            console.print(f"Count: {len(responses)}")
            console.print(f"Dimensions: {len(responses[0].embedding) if responses else 'N/A'}")

    except Exception as e:
        print_error(f"Batch embedding failed: {e}")


def _get_embedding_provider(provider: str, model: str):
    """Get an embedding-capable provider instance."""
    if provider == "openai":
        from ..providers.openai.client import OpenAIProvider
        return OpenAIProvider(model=model)
    elif provider == "gemini":
        from ..providers.gemini.client import GeminiProvider
        return GeminiProvider(model=model)
    elif provider == "mistral":
        from ..providers.mistral.client import MistralProvider
        return MistralProvider(model=model)
    elif provider == "cohere":
        from ..providers.cohere.client import CohereProvider
        return CohereProvider(model=model)
    else:
        raise ValueError(f"Provider '{provider}' does not support embeddings")
