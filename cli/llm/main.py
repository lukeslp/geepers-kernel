#!/usr/bin/env python3
"""
Unified LLM CLI - Main Entry Point

A comprehensive CLI for multiple LLM providers with unified interface
and provider-specific capabilities.

Author: Luke Steuber
"""

import os
import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from . import __version__
from .config import Config, get_config
from .providers import PROVIDERS, get_provider, get_available_providers

# Initialize Typer app and Rich console
app = typer.Typer(
    name="llm",
    help="Unified LLM CLI - Chat, vision, audio, video, and more across multiple providers",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


# =============================================================================
# Unified Commands (auto-select provider)
# =============================================================================

@app.command()
def chat(
    prompt: str = typer.Argument(..., help="The prompt to send"),
    provider: str = typer.Option("auto", "-p", "--provider", help="Provider to use (auto, gemini, openai, claude, xai, mistral, cohere, perplexity)"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Specific model to use"),
    system: Optional[str] = typer.Option(None, "-s", "--system", help="System prompt"),
    temperature: float = typer.Option(0.7, "-t", "--temperature", help="Temperature (0.0-2.0)"),
    max_tokens: int = typer.Option(4096, "--max-tokens", help="Maximum tokens in response"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream response"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Chat with an LLM. Auto-selects the best available provider if not specified.

    Examples:
        llm chat "explain quantum computing"
        llm chat -p gemini "hello world"
        llm chat -m gpt-4o "complex question"
    """
    from .core.chat import unified_chat
    unified_chat(
        prompt=prompt,
        provider=provider,
        model=model,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        json_output=json_output,
    )


@app.command()
def vision(
    image: Path = typer.Argument(..., help="Image file to analyze"),
    prompt: str = typer.Argument("Describe this image in detail", help="Prompt for analysis"),
    provider: str = typer.Option("auto", "-p", "--provider", help="Provider to use"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Specific model"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Analyze an image with vision-capable LLM.

    Examples:
        llm vision photo.jpg "what's in this image?"
        llm vision -p gemini screenshot.png "extract text"
    """
    from .core.vision import unified_vision
    unified_vision(
        image=image,
        prompt=prompt,
        provider=provider,
        model=model,
        json_output=json_output,
    )


@app.command()
def audio(
    file: Path = typer.Argument(..., help="Audio file to process"),
    prompt: str = typer.Argument("Transcribe this audio", help="Prompt for processing"),
    provider: str = typer.Option("auto", "-p", "--provider", help="Provider to use"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Process audio with LLM (transcription, analysis).

    Examples:
        llm audio meeting.mp3 "transcribe and summarize"
        llm audio -p gemini podcast.wav "identify speakers"
    """
    from .core.audio import unified_audio
    unified_audio(
        file=file,
        prompt=prompt,
        provider=provider,
        json_output=json_output,
    )


@app.command()
def embed(
    text: str = typer.Argument(..., help="Text to embed"),
    provider: str = typer.Option("auto", "-p", "--provider", help="Provider to use"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Specific model"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Save embeddings to file"),
):
    """
    Generate text embeddings.

    Examples:
        llm embed "semantic search query"
        llm embed -p openai "text to embed" -o vectors.json
    """
    from .core.embed import unified_embed
    unified_embed(
        text=text,
        provider=provider,
        model=model,
        output=output,
    )


# =============================================================================
# Utility Commands
# =============================================================================

@app.command()
def providers():
    """
    List all available providers and their status.
    """
    config = get_config()

    table = Table(
        title="LLM Providers",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Provider", style="bold")
    table.add_column("Status")
    table.add_column("Default Model", style="dim")
    table.add_column("Capabilities")

    for name, info in PROVIDERS.items():
        has_key = config.has_api_key(name)
        status = "[green]Ready[/green]" if has_key else "[red]No API Key[/red]"

        caps = []
        if info.get("text"): caps.append("text")
        if info.get("vision"): caps.append("vision")
        if info.get("audio"): caps.append("audio")
        if info.get("video"): caps.append("video")
        if info.get("image_gen"): caps.append("img-gen")
        if info.get("tts"): caps.append("tts")
        if info.get("embedding"): caps.append("embed")

        table.add_row(
            name,
            status,
            info.get("default_model", "N/A"),
            ", ".join(caps) if caps else "text",
        )

    console.print(table)

    # Show configuration hint
    console.print("\n[dim]API keys are loaded from environment variables:[/dim]")
    for name, info in PROVIDERS.items():
        env_key = info.get("env_key", f"{name.upper()}_API_KEY")
        console.print(f"  [cyan]{env_key}[/cyan]")


@app.command()
def models(
    provider: Optional[str] = typer.Argument(None, help="Provider to list models for"),
):
    """
    List available models for a provider.

    Examples:
        llm models           # List all default models
        llm models gemini    # List Gemini models
    """
    from .core.models import list_models
    list_models(provider)


@app.command()
def config(
    action: Optional[str] = typer.Argument(None, help="Action: show, set, get"),
    key: Optional[str] = typer.Argument(None, help="Configuration key"),
    value: Optional[str] = typer.Argument(None, help="Value to set"),
):
    """
    Manage CLI configuration.

    Examples:
        llm config                           # Show all config
        llm config set default_provider gemini
        llm config get default_provider
    """
    cfg = get_config()

    if action is None or action == "show":
        console.print(Panel(
            f"""[bold]Current Configuration[/bold]

Default Provider: [cyan]{cfg.default_provider}[/cyan]
Config File: [dim]{cfg.config_path}[/dim]

[bold]Provider Settings:[/bold]""",
            title="LLM CLI Config",
            border_style="blue",
        ))
        for name in PROVIDERS:
            model = cfg.get_provider_model(name)
            if model:
                console.print(f"  {name}.model = [cyan]{model}[/cyan]")

    elif action == "set" and key and value:
        cfg.set(key, value)
        console.print(f"[green]Set {key} = {value}[/green]")

    elif action == "get" and key:
        val = cfg.get(key)
        console.print(f"{key} = [cyan]{val}[/cyan]" if val else f"[dim]{key} not set[/dim]")

    else:
        console.print("[red]Usage: llm config [show|set|get] [key] [value][/red]")


@app.command()
def version():
    """Show version information."""
    console.print(Panel(
        f"""[bold cyan]LLM CLI v{__version__}[/bold cyan]

Unified command-line interface for multiple LLM providers.

[bold]Supported Providers:[/bold]
  Gemini, OpenAI, Anthropic, xAI, Mistral, Cohere, Perplexity

[bold]Author:[/bold] Luke Steuber
[bold]Location:[/bold] /home/coolhand/shared/cli/llm/""",
        title="Version Info",
        border_style="cyan",
    ))


# =============================================================================
# Provider Subcommands (registered dynamically)
# =============================================================================

def register_provider_commands():
    """Register provider-specific subcommands."""
    try:
        from .providers.gemini.commands import app as gemini_app
        app.add_typer(gemini_app, name="gemini", help="Google Gemini commands")
    except ImportError:
        pass

    try:
        from .providers.openai.commands import app as openai_app
        app.add_typer(openai_app, name="openai", help="OpenAI commands")
    except ImportError:
        pass

    try:
        from .providers.anthropic.commands import app as anthropic_app
        app.add_typer(anthropic_app, name="claude", help="Anthropic Claude commands")
    except ImportError:
        pass

    try:
        from .providers.xai.commands import app as xai_app
        app.add_typer(xai_app, name="xai", help="xAI Grok commands")
    except ImportError:
        pass

    try:
        from .providers.mistral.commands import app as mistral_app
        app.add_typer(mistral_app, name="mistral", help="Mistral AI commands")
    except ImportError:
        pass

    try:
        from .providers.cohere.commands import app as cohere_app
        app.add_typer(cohere_app, name="cohere", help="Cohere commands")
    except ImportError:
        pass

    try:
        from .providers.perplexity.commands import app as perplexity_app
        app.add_typer(perplexity_app, name="perplexity", help="Perplexity commands")
    except ImportError:
        pass


# Register provider commands on import
register_provider_commands()


# =============================================================================
# Main callback
# =============================================================================

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    show_version: bool = typer.Option(False, "--version", "-v", help="Show version"),
):
    """
    LLM CLI - Unified interface for multiple LLM providers.

    Quick Start:
        llm chat "hello world"              # Chat with default provider
        llm gemini chat "hello"             # Use specific provider
        llm vision image.png "describe"     # Analyze images
        llm providers                       # Check provider status
    """
    if show_version:
        version()
        raise typer.Exit()


def cli():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    cli()
