"""
xAI CLI Commands.

Typer subcommands for Grok and Aurora.

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
from .client import XAIProvider

app = typer.Typer(
    name="xai",
    help="xAI Grok API commands",
    no_args_is_help=True,
)
console = Console()


# =========================================================================
# Text Commands
# =========================================================================

@app.command("chat")
def chat(
    prompt: str = typer.Argument(..., help="The prompt to send"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model (grok-3, grok-3-fast, grok-2)"),
    system: Optional[str] = typer.Option(None, "-s", "--system", help="System prompt"),
    temperature: float = typer.Option(0.7, "-t", "--temperature", help="Temperature (0.0-2.0)"),
    max_tokens: int = typer.Option(4096, "--max-tokens", help="Max tokens in response"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Chat with Grok.

    Example: llm xai chat "Explain this meme"
    Example: llm xai chat -m grok-3-fast "Quick question"
    """
    try:
        provider = XAIProvider(model=model)

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
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model (grok-2-vision)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Analyze an image with Grok Vision.

    Example: llm xai vision meme.jpg "What's funny about this?"
    """
    if not image.exists():
        print_error(f"Image not found: {image}")
        raise typer.Exit(1)

    if not is_image(image):
        print_error(f"Not a supported image format: {image.suffix}")
        raise typer.Exit(1)

    try:
        provider = XAIProvider(model=model)

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
    Compare multiple images with Grok Vision.

    Example: llm xai compare img1.png img2.png -p "What are the differences?"
    """
    for img in images:
        if not img.exists():
            print_error(f"Image not found: {img}")
            raise typer.Exit(1)
        if not is_image(img):
            print_error(f"Not a supported image format: {img.suffix}")
            raise typer.Exit(1)

    try:
        provider = XAIProvider(model=model)

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
# Aurora Commands
# =========================================================================

@app.command("aurora")
def aurora(
    prompt: str = typer.Argument(..., help="Image generation prompt"),
    output: Path = typer.Option(Path("generated.png"), "-o", "--output", help="Output file"),
    size: str = typer.Option("1024x1024", "-s", "--size", help="Image size"),
    count: int = typer.Option(1, "-n", "--count", help="Number of images to generate"),
):
    """
    Generate images with Aurora.

    Example: llm xai aurora "a space battle scene" -o space.png
    Example: llm xai aurora "cyberpunk city" -n 4
    """
    try:
        provider = XAIProvider()

        with create_spinner(f"Generating {count} image(s) with Aurora..."):
            response = provider.generate_image(
                prompt=prompt,
                size=size,
                n=count,
            )

        for i, img_data in enumerate(response.images):
            if count == 1:
                out_path = output
            else:
                out_path = output.parent / f"{output.stem}_{i+1}{output.suffix}"

            with open(out_path, "wb") as f:
                f.write(img_data)
            console.print(f"[green]Saved: {out_path}[/green]")

        if response.revised_prompt:
            console.print(f"\n[dim]Revised prompt: {response.revised_prompt}[/dim]")

    except Exception as e:
        print_error(f"Image generation failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Utility Commands
# =========================================================================

@app.command("models")
def models(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List available xAI models.

    Example: llm xai models
    """
    try:
        provider = XAIProvider()
        model_list = provider.list_models()

        if json_output:
            print_json(model_list)
        else:
            from rich.table import Table
            table = Table(title="xAI Models")
            table.add_column("Model", style="cyan")
            table.add_column("Description")
            table.add_column("Context", style="dim")

            for m in model_list:
                ctx = f"{m.get('context_window', 0) // 1000}K" if m.get('context_window') else ""
                table.add_row(m["name"], m.get("description", ""), ctx)

            console.print(table)

    except Exception as e:
        print_error(f"Failed to list models: {e}")
        raise typer.Exit(1)
