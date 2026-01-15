"""
Mistral CLI Commands.

Author: Luke Steuber
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from ...utils import print_response, print_error, print_json, is_image, create_spinner
from .client import MistralProvider

app = typer.Typer(name="mistral", help="Mistral AI commands", no_args_is_help=True)
console = Console()


@app.command("chat")
def chat(
    prompt: str = typer.Argument(..., help="The prompt to send"),
    model: Optional[str] = typer.Option(None, "-m", "--model"),
    system: Optional[str] = typer.Option(None, "-s", "--system"),
    temperature: float = typer.Option(0.7, "-t", "--temperature"),
    max_tokens: int = typer.Option(4096, "--max-tokens"),
    no_stream: bool = typer.Option(False, "--no-stream"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Chat with Mistral."""
    try:
        provider = MistralProvider(model=model)
        from ...providers.base import Message
        messages = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))

        if no_stream or json_output:
            with create_spinner("Thinking..."):
                response = provider.chat(messages=messages, temperature=temperature, max_tokens=max_tokens)
            if json_output:
                print_json({"content": response.content, "model": response.model, "usage": response.usage})
            else:
                print_response(response.content)
        else:
            full_response = ""
            with Live(Markdown(""), console=console, refresh_per_second=10) as live:
                for chunk in provider.chat_stream(messages=messages, temperature=temperature, max_tokens=max_tokens):
                    full_response += chunk
                    live.update(Markdown(full_response))
            console.print()
    except Exception as e:
        print_error(f"Chat failed: {e}")
        raise typer.Exit(1)


@app.command("vision")
def vision(
    image: Path = typer.Argument(..., help="Path to image file"),
    prompt: str = typer.Argument("Describe this image in detail"),
    model: Optional[str] = typer.Option(None, "-m", "--model"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Analyze an image with Pixtral."""
    if not image.exists():
        print_error(f"Image not found: {image}")
        raise typer.Exit(1)
    if not is_image(image):
        print_error(f"Not a supported image format: {image.suffix}")
        raise typer.Exit(1)

    try:
        provider = MistralProvider(model=model)
        with create_spinner("Analyzing image..."):
            response = provider.analyze_image(image=image, prompt=prompt)
        if json_output:
            print_json({"content": response.content, "model": response.model, "usage": response.usage})
        else:
            print_response(response.content, title="Image Analysis")
    except Exception as e:
        print_error(f"Vision analysis failed: {e}")
        raise typer.Exit(1)


@app.command("embed")
def embed(
    text: str = typer.Argument(..., help="Text to embed"),
    model: Optional[str] = typer.Option(None, "-m", "--model"),
    output: Optional[Path] = typer.Option(None, "-o", "--output"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Generate text embeddings."""
    try:
        provider = MistralProvider()
        with create_spinner("Generating embedding..."):
            response = provider.embed(text=text, model=model)
        result = {"embedding": response.embedding, "dimensions": len(response.embedding), "model": response.model}
        if output:
            import json
            with open(output, "w") as f:
                json.dump(result, f, indent=2)
            console.print(f"[green]Saved: {output}[/green]")
        elif json_output:
            print_json(result)
        else:
            console.print(f"[bold]Embedding Generated[/bold]")
            console.print(f"Dimensions: {len(response.embedding)}")
            console.print(response.embedding[:10])
    except Exception as e:
        print_error(f"Embedding failed: {e}")
        raise typer.Exit(1)


@app.command("models")
def models(json_output: bool = typer.Option(False, "--json")):
    """List available Mistral models."""
    try:
        provider = MistralProvider()
        model_list = provider.list_models()
        if json_output:
            print_json(model_list)
        else:
            from rich.table import Table
            table = Table(title="Mistral Models")
            table.add_column("Model", style="cyan")
            table.add_column("Description")
            for m in model_list:
                table.add_row(m["name"], m.get("description", ""))
            console.print(table)
    except Exception as e:
        print_error(f"Failed to list models: {e}")
        raise typer.Exit(1)
