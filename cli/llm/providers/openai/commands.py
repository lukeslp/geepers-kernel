"""
OpenAI CLI Commands.

Typer subcommands for OpenAI API (GPT-4, DALL-E, Whisper, TTS).

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
    is_audio,
    create_spinner,
)
from .client import OpenAIProvider

app = typer.Typer(
    name="openai",
    help="OpenAI API commands (GPT-4, DALL-E, Whisper, TTS)",
    no_args_is_help=True,
)
console = Console()


# =========================================================================
# Text Commands
# =========================================================================

@app.command("chat")
def chat(
    prompt: str = typer.Argument(..., help="The prompt to send"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model (gpt-4o, gpt-4o-mini, o1)"),
    system: Optional[str] = typer.Option(None, "-s", "--system", help="System prompt"),
    temperature: float = typer.Option(0.7, "-t", "--temperature", help="Temperature (0.0-2.0)"),
    max_tokens: int = typer.Option(4096, "--max-tokens", help="Max tokens in response"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Chat with GPT-4.

    Example: llm openai chat "Explain neural networks"
    Example: llm openai chat -m gpt-4o-mini "Quick question"
    """
    try:
        provider = OpenAIProvider(model=model)

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
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model (gpt-4o, gpt-4o-mini)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Analyze an image with GPT-4 Vision.

    Example: llm openai vision photo.jpg "What's in this image?"
    """
    if not image.exists():
        print_error(f"Image not found: {image}")
        raise typer.Exit(1)

    if not is_image(image):
        print_error(f"Not a supported image format: {image.suffix}")
        raise typer.Exit(1)

    try:
        provider = OpenAIProvider(model=model)

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


# =========================================================================
# Whisper Commands
# =========================================================================

@app.command("whisper")
def whisper(
    file: Path = typer.Argument(..., help="Path to audio file"),
    prompt: Optional[str] = typer.Option(None, "-p", "--prompt", help="Guide prompt"),
    language: Optional[str] = typer.Option(None, "-l", "--language", help="ISO-639-1 language code"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Transcribe audio with Whisper.

    Example: llm openai whisper recording.mp3
    Example: llm openai whisper audio.wav -l en
    """
    if not file.exists():
        print_error(f"Audio file not found: {file}")
        raise typer.Exit(1)

    if not is_audio(file):
        print_error(f"Not a supported audio format: {file.suffix}")
        raise typer.Exit(1)

    try:
        provider = OpenAIProvider()

        with create_spinner("Transcribing audio..."):
            response = provider.analyze_audio(
                audio=file,
                prompt=prompt or "Transcribe this audio",
                language=language,
            )

        if json_output:
            print_json({
                "transcription": response.content,
                "model": response.model,
            })
        else:
            print_response(response.content, title="Transcription")

    except Exception as e:
        print_error(f"Transcription failed: {e}")
        raise typer.Exit(1)


@app.command("translate")
def translate_audio(
    file: Path = typer.Argument(..., help="Path to audio file"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Translate audio to English with Whisper.

    Example: llm openai translate foreign_audio.mp3
    """
    if not file.exists():
        print_error(f"Audio file not found: {file}")
        raise typer.Exit(1)

    try:
        provider = OpenAIProvider()

        with create_spinner("Translating audio to English..."):
            response = provider.translate_audio(audio=file)

        if json_output:
            print_json({
                "translation": response.content,
                "model": response.model,
            })
        else:
            print_response(response.content, title="English Translation")

    except Exception as e:
        print_error(f"Translation failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# DALL-E Commands
# =========================================================================

@app.command("dalle")
def dalle(
    prompt: str = typer.Argument(..., help="Image generation prompt"),
    output: Path = typer.Option(Path("generated.png"), "-o", "--output", help="Output file"),
    model: str = typer.Option("dall-e-3", "-m", "--model", help="Model (dall-e-3, dall-e-2)"),
    size: str = typer.Option("1024x1024", "-s", "--size", help="Size (1024x1024, 1792x1024, 1024x1792)"),
    quality: str = typer.Option("standard", "-q", "--quality", help="Quality (standard, hd)"),
    style: str = typer.Option("vivid", "--style", help="Style (vivid, natural)"),
    count: int = typer.Option(1, "-n", "--count", help="Number of images (1 for DALL-E 3)"),
):
    """
    Generate images with DALL-E.

    Example: llm openai dalle "a sunset over mountains" -o sunset.png
    Example: llm openai dalle "cyberpunk city" -s 1792x1024 -q hd
    """
    try:
        provider = OpenAIProvider()

        with create_spinner(f"Generating image with {model}..."):
            response = provider.generate_image(
                prompt=prompt,
                model=model,
                size=size,
                n=count,
                quality=quality,
                style=style,
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
# TTS Commands
# =========================================================================

@app.command("tts")
def tts(
    text: str = typer.Argument(..., help="Text to convert to speech"),
    output: Path = typer.Option(Path("speech.mp3"), "-o", "--output", help="Output audio file"),
    model: str = typer.Option("tts-1", "-m", "--model", help="Model (tts-1, tts-1-hd)"),
    voice: str = typer.Option("alloy", "-v", "--voice", help="Voice (alloy, echo, fable, onyx, nova, shimmer)"),
    speed: float = typer.Option(1.0, "-s", "--speed", help="Speed (0.25 to 4.0)"),
    format: str = typer.Option("mp3", "-f", "--format", help="Format (mp3, opus, aac, flac)"),
):
    """
    Generate speech from text.

    Example: llm openai tts "Hello world!" -o hello.mp3
    Example: llm openai tts "Welcome" -v nova -m tts-1-hd
    """
    try:
        provider = OpenAIProvider()

        with create_spinner("Generating speech..."):
            response = provider.generate_speech(
                text=text,
                model=model,
                voice=voice,
                speed=speed,
                response_format=format,
            )

        with open(output, "wb") as f:
            f.write(response.audio)
        console.print(f"[green]Saved: {output}[/green]")

    except Exception as e:
        print_error(f"Speech generation failed: {e}")
        raise typer.Exit(1)


@app.command("tts-file")
def tts_file(
    file: Path = typer.Argument(..., help="Text file to read"),
    output: Path = typer.Option(Path("speech.mp3"), "-o", "--output", help="Output audio file"),
    model: str = typer.Option("tts-1", "-m", "--model", help="Model"),
    voice: str = typer.Option("alloy", "-v", "--voice", help="Voice"),
    speed: float = typer.Option(1.0, "-s", "--speed", help="Speed"),
):
    """
    Generate speech from a text file.

    Example: llm openai tts-file script.txt -o audiobook.mp3
    """
    if not file.exists():
        print_error(f"File not found: {file}")
        raise typer.Exit(1)

    try:
        text = file.read_text()
        provider = OpenAIProvider()

        with create_spinner("Generating speech from file..."):
            response = provider.generate_speech(
                text=text,
                model=model,
                voice=voice,
                speed=speed,
            )

        with open(output, "wb") as f:
            f.write(response.audio)
        console.print(f"[green]Saved: {output}[/green]")

    except Exception as e:
        print_error(f"Speech generation failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Embedding Commands
# =========================================================================

@app.command("embed")
def embed(
    text: str = typer.Argument(..., help="Text to embed"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model"),
    dimensions: Optional[int] = typer.Option(None, "-d", "--dimensions", help="Output dimensions"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Save to JSON file"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Generate text embeddings.

    Example: llm openai embed "semantic search query"
    Example: llm openai embed "text" -m text-embedding-3-large -d 1024
    """
    try:
        provider = OpenAIProvider()

        with create_spinner("Generating embedding..."):
            response = provider.embed(
                text=text,
                model=model,
                dimensions=dimensions,
            )

        result = {
            "embedding": response.embedding,
            "dimensions": len(response.embedding),
            "model": response.model,
            "usage": response.usage,
        }

        if output:
            import json
            with open(output, "w") as f:
                json.dump(result, f, indent=2)
            console.print(f"[green]Saved: {output}[/green]")
        elif json_output:
            print_json(result)
        else:
            console.print(f"[bold]Embedding Generated[/bold]")
            console.print(f"Model: {response.model}")
            console.print(f"Dimensions: {len(response.embedding)}")
            console.print("\n[dim]First 10 values:[/dim]")
            console.print(response.embedding[:10])

    except Exception as e:
        print_error(f"Embedding failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Utility Commands
# =========================================================================

@app.command("models")
def models(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List available OpenAI models.

    Example: llm openai models
    """
    try:
        provider = OpenAIProvider()
        model_list = provider.list_models()

        if json_output:
            print_json(model_list)
        else:
            from rich.table import Table
            table = Table(title="OpenAI Models")
            table.add_column("Model", style="cyan")
            table.add_column("Owner", style="dim")

            # Filter to relevant models
            relevant = [m for m in model_list if any(x in m["name"] for x in ["gpt", "dall", "whisper", "tts", "embed"])]

            for m in sorted(relevant, key=lambda x: x["name"]):
                table.add_row(m["name"], m.get("owned_by", ""))

            console.print(table)

    except Exception as e:
        print_error(f"Failed to list models: {e}")
        raise typer.Exit(1)
