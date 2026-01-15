"""
Anthropic CLI Commands.

Typer subcommands for Claude models.

Author: Luke Steuber
"""

from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from ...utils import (
    print_response,
    print_error,
    print_json,
    is_image,
    create_spinner,
)
from .client import AnthropicProvider

app = typer.Typer(
    name="claude",
    help="Anthropic Claude API commands",
    no_args_is_help=True,
)
console = Console()


# =========================================================================
# Text Commands
# =========================================================================

@app.command("chat")
def chat(
    prompt: str = typer.Argument(..., help="The prompt to send"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model (claude-sonnet-4, claude-opus-4)"),
    system: Optional[str] = typer.Option(None, "-s", "--system", help="System prompt"),
    temperature: float = typer.Option(0.7, "-t", "--temperature", help="Temperature (0.0-1.0)"),
    max_tokens: int = typer.Option(4096, "--max-tokens", help="Max tokens in response"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Chat with Claude.

    Example: llm claude chat "Explain quantum computing"
    Example: llm claude chat -m claude-opus-4-20250514 "Complex analysis"
    """
    try:
        provider = AnthropicProvider(model=model)

        from ...providers.base import Message
        messages = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))

        if no_stream or json_output:
            with create_spinner("Thinking..."):
                response = provider.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            if json_output:
                print_json({
                    "content": response.content,
                    "model": response.model,
                    "usage": response.usage,
                })
            else:
                print_response(response.content)
        else:
            full_response = ""
            with Live(Markdown(""), console=console, refresh_per_second=10) as live:
                for chunk in provider.chat_stream(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    full_response += chunk
                    live.update(Markdown(full_response))
            console.print()

    except Exception as e:
        print_error(f"Chat failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Vision Commands
# =========================================================================

@app.command("vision")
def vision(
    image: Path = typer.Argument(..., help="Path to image file"),
    prompt: str = typer.Argument("Describe this image in detail", help="Analysis prompt"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Analyze an image with Claude Vision.

    Example: llm claude vision photo.jpg "What's in this image?"
    """
    if not image.exists():
        print_error(f"Image not found: {image}")
        raise typer.Exit(1)

    if not is_image(image):
        print_error(f"Not a supported image format: {image.suffix}")
        raise typer.Exit(1)

    try:
        provider = AnthropicProvider(model=model)

        with create_spinner("Analyzing image..."):
            response = provider.analyze_image(
                image=image,
                prompt=prompt,
            )

        if json_output:
            print_json({
                "content": response.content,
                "model": response.model,
                "usage": response.usage,
            })
        else:
            print_response(response.content, title="Image Analysis")

    except Exception as e:
        print_error(f"Vision analysis failed: {e}")
        raise typer.Exit(1)


@app.command("compare")
def compare_images(
    images: List[Path] = typer.Argument(..., help="Image files to compare"),
    prompt: str = typer.Option("Compare these images", "-p", "--prompt", help="Comparison prompt"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Compare multiple images with Claude Vision.

    Example: llm claude compare img1.png img2.png -p "What are the differences?"
    """
    for img in images:
        if not img.exists():
            print_error(f"Image not found: {img}")
            raise typer.Exit(1)
        if not is_image(img):
            print_error(f"Not a supported image format: {img.suffix}")
            raise typer.Exit(1)

    try:
        provider = AnthropicProvider(model=model)

        with create_spinner(f"Comparing {len(images)} images..."):
            response = provider.analyze_images(
                images=images,
                prompt=prompt,
            )

        if json_output:
            print_json({
                "content": response.content,
                "model": response.model,
                "usage": response.usage,
            })
        else:
            print_response(response.content, title="Image Comparison")

    except Exception as e:
        print_error(f"Image comparison failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Utility Commands
# =========================================================================

@app.command("models")
def models(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List available Claude models.

    Example: llm claude models
    """
    try:
        provider = AnthropicProvider()
        model_list = provider.list_models()

        if json_output:
            print_json(model_list)
        else:
            from rich.table import Table
            table = Table(title="Claude Models")
            table.add_column("Model", style="cyan")
            table.add_column("Description")
            table.add_column("Context", style="dim")

            for m in model_list:
                ctx = f"{m['context_window'] // 1000}K"
                table.add_row(m["name"], m.get("description", ""), ctx)

            console.print(table)

    except Exception as e:
        print_error(f"Failed to list models: {e}")
        raise typer.Exit(1)
