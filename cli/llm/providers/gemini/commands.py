"""
Gemini CLI Commands.

Typer subcommands for the full Gemini API suite.

Author: Luke Steuber
"""

from pathlib import Path
from typing import Optional, List
import sys

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
    is_video,
    is_document,
    create_spinner,
)
from .client import GeminiProvider

app = typer.Typer(
    name="gemini",
    help="Google Gemini API commands",
    no_args_is_help=True,
)
console = Console()


# =========================================================================
# Text Commands
# =========================================================================

@app.command("chat")
def chat(
    prompt: str = typer.Argument(..., help="The prompt to send"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    system: Optional[str] = typer.Option(None, "-s", "--system", help="System prompt"),
    temperature: float = typer.Option(0.7, "-t", "--temperature", help="Temperature (0.0-2.0)"),
    max_tokens: int = typer.Option(4096, "--max-tokens", help="Max tokens in response"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Chat with Gemini.

    Example: llm gemini chat "Explain quantum computing"
    """
    try:
        provider = GeminiProvider(model=model)

        # Build messages
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
            # Streaming
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
    Analyze an image with Gemini.

    Example: llm gemini vision photo.jpg "What's in this image?"
    """
    if not image.exists():
        print_error(f"Image not found: {image}")
        raise typer.Exit(1)

    if not is_image(image):
        print_error(
            f"Not a supported image format: {image.suffix}",
            "Supported: PNG, JPEG, WEBP, HEIC, HEIF, GIF, BMP, TIFF"
        )
        raise typer.Exit(1)

    try:
        provider = GeminiProvider(model=model)

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
                "image": str(image),
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
    Compare multiple images.

    Example: llm gemini compare img1.png img2.png -p "What are the differences?"
    """
    for img in images:
        if not img.exists():
            print_error(f"Image not found: {img}")
            raise typer.Exit(1)
        if not is_image(img):
            print_error(f"Not a supported image format: {img.suffix}")
            raise typer.Exit(1)

    try:
        provider = GeminiProvider(model=model)

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
                "images": [str(img) for img in images],
            })
        else:
            print_response(response.content, title="Image Comparison")

    except Exception as e:
        print_error(f"Image comparison failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Audio Commands
# =========================================================================

@app.command("audio")
def audio(
    file: Path = typer.Argument(..., help="Path to audio file"),
    prompt: str = typer.Argument("Transcribe this audio", help="Processing prompt"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Analyze or transcribe audio with Gemini.

    Example: llm gemini audio recording.mp3 "Transcribe this"
    Example: llm gemini audio podcast.wav "Summarize the key points"
    """
    if not file.exists():
        print_error(f"Audio file not found: {file}")
        raise typer.Exit(1)

    if not is_audio(file):
        print_error(
            f"Not a supported audio format: {file.suffix}",
            "Supported: MP3, WAV, AIFF, AAC, OGG, FLAC, M4A"
        )
        raise typer.Exit(1)

    try:
        provider = GeminiProvider(model=model)

        with create_spinner("Processing audio..."):
            response = provider.analyze_audio(
                audio=file,
                prompt=prompt,
            )

        if json_output:
            print_json({
                "content": response.content,
                "model": response.model,
                "usage": response.usage,
                "audio_file": str(file),
            })
        else:
            print_response(response.content, title="Audio Analysis")

    except Exception as e:
        print_error(f"Audio processing failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Video Commands
# =========================================================================

@app.command("video")
def video(
    file: Path = typer.Argument(..., help="Path to video file"),
    prompt: str = typer.Argument("Describe this video", help="Analysis prompt"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Analyze a video with Gemini.

    Supports videos up to 6 hours with Gemini's 2M token context.

    Example: llm gemini video presentation.mp4 "Summarize the key points"
    """
    if not file.exists():
        print_error(f"Video file not found: {file}")
        raise typer.Exit(1)

    if not is_video(file):
        print_error(
            f"Not a supported video format: {file.suffix}",
            "Supported: MP4, MPEG, MOV, AVI, FLV, MPG, WEBM, WMV, 3GP"
        )
        raise typer.Exit(1)

    try:
        provider = GeminiProvider(model=model)

        with create_spinner("Analyzing video (this may take a while for large files)..."):
            response = provider.analyze_video(
                video=file,
                prompt=prompt,
            )

        if json_output:
            print_json({
                "content": response.content,
                "model": response.model,
                "usage": response.usage,
                "video_file": str(file),
            })
        else:
            print_response(response.content, title="Video Analysis")

    except Exception as e:
        print_error(f"Video analysis failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Document Commands
# =========================================================================

@app.command("doc")
def document(
    file: Path = typer.Argument(..., help="Path to document (PDF)"),
    prompt: str = typer.Argument("Summarize this document", help="Analysis prompt"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Analyze a document with Gemini.

    Supports PDFs up to 50MB and 1000 pages.

    Example: llm gemini doc research.pdf "Extract the key findings"
    """
    if not file.exists():
        print_error(f"Document not found: {file}")
        raise typer.Exit(1)

    if not is_document(file):
        print_error(
            f"Not a supported document format: {file.suffix}",
            "Supported: PDF"
        )
        raise typer.Exit(1)

    try:
        provider = GeminiProvider(model=model)

        with create_spinner("Processing document..."):
            response = provider.analyze_document(
                document=file,
                prompt=prompt,
            )

        if json_output:
            print_json({
                "content": response.content,
                "model": response.model,
                "usage": response.usage,
                "document": str(file),
            })
        else:
            print_response(response.content, title="Document Analysis")

    except Exception as e:
        print_error(f"Document processing failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Image Generation Commands
# =========================================================================

@app.command("imagine")
def imagine(
    prompt: str = typer.Argument(..., help="Image generation prompt"),
    output: Path = typer.Option(Path("generated.png"), "-o", "--output", help="Output file"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    aspect_ratio: str = typer.Option("1:1", "-a", "--aspect", help="Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)"),
    count: int = typer.Option(1, "-n", "--count", help="Number of images to generate"),
):
    """
    Generate images with Imagen.

    Example: llm gemini imagine "a sunset over mountains" -o sunset.png
    Example: llm gemini imagine "cyberpunk city" -a 16:9 -n 4
    """
    try:
        provider = GeminiProvider(model=model)

        with create_spinner(f"Generating {count} image(s)..."):
            response = provider.generate_image(
                prompt=prompt,
                n=count,
                aspect_ratio=aspect_ratio,
            )

        # Save images
        for i, img_data in enumerate(response.images):
            if count == 1:
                out_path = output
            else:
                out_path = output.parent / f"{output.stem}_{i+1}{output.suffix}"

            with open(out_path, "wb") as f:
                f.write(img_data)
            console.print(f"[green]Saved: {out_path}[/green]")

    except Exception as e:
        print_error(f"Image generation failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Text-to-Speech Commands
# =========================================================================

@app.command("speak")
def speak(
    text: str = typer.Argument(..., help="Text to convert to speech"),
    output: Path = typer.Option(Path("speech.wav"), "-o", "--output", help="Output audio file"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    voice: str = typer.Option("Puck", "-v", "--voice", help="Voice (Puck, Charon, Kore, Fenrir, Aoede)"),
):
    """
    Generate speech from text.

    Example: llm gemini speak "Hello, world!" -o hello.wav
    Example: llm gemini speak "Welcome to the show" -v Charon
    """
    try:
        provider = GeminiProvider(model=model)

        with create_spinner("Generating speech..."):
            response = provider.generate_speech(
                text=text,
                voice=voice,
            )

        with open(output, "wb") as f:
            f.write(response.audio)
        console.print(f"[green]Saved: {output}[/green]")

    except Exception as e:
        print_error(f"Speech generation failed: {e}")
        raise typer.Exit(1)


@app.command("speak-file")
def speak_file(
    file: Path = typer.Argument(..., help="Text file to read"),
    output: Path = typer.Option(Path("speech.wav"), "-o", "--output", help="Output audio file"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    voice: str = typer.Option("Puck", "-v", "--voice", help="Voice name"),
):
    """
    Generate speech from a text file.

    Example: llm gemini speak-file script.txt -o audiobook.wav
    """
    if not file.exists():
        print_error(f"File not found: {file}")
        raise typer.Exit(1)

    try:
        text = file.read_text()
        provider = GeminiProvider(model=model)

        with create_spinner("Generating speech from file..."):
            response = provider.generate_speech(
                text=text,
                voice=voice,
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
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Save to JSON file"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Generate text embeddings.

    Example: llm gemini embed "semantic search query"
    Example: llm gemini embed "document text" -o embedding.json
    """
    try:
        provider = GeminiProvider(model=model)

        with create_spinner("Generating embedding..."):
            response = provider.embed(text=text)

        result = {
            "embedding": response.embedding,
            "dimensions": len(response.embedding),
            "model": response.model,
        }

        if output:
            import json
            with open(output, "w") as f:
                json.dump(result, f, indent=2)
            console.print(f"[green]Saved: {output}[/green]")
            console.print(f"Dimensions: {len(response.embedding)}")
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
# Files API Commands
# =========================================================================

@app.command("upload")
def upload_file(
    file: Path = typer.Argument(..., help="File to upload"),
    name: Optional[str] = typer.Option(None, "-n", "--name", help="Display name"),
):
    """
    Upload a file to Gemini Files API.

    Useful for large files that exceed inline limits.

    Example: llm gemini upload large_video.mp4
    """
    if not file.exists():
        print_error(f"File not found: {file}")
        raise typer.Exit(1)

    try:
        provider = GeminiProvider()

        with create_spinner(f"Uploading {file.name}..."):
            uploaded = provider.upload_file(file, display_name=name)

        console.print(f"[green]Uploaded successfully![/green]")
        console.print(f"Name: {uploaded.name}")
        console.print(f"URI: {uploaded.uri}")
        console.print(f"MIME Type: {uploaded.mime_type}")

    except Exception as e:
        print_error(f"Upload failed: {e}")
        raise typer.Exit(1)


@app.command("files")
def list_files(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List uploaded files.

    Example: llm gemini files
    """
    try:
        provider = GeminiProvider()
        files = provider.list_files()

        if json_output:
            print_json([{
                "name": f.name,
                "display_name": f.display_name,
                "mime_type": f.mime_type,
                "uri": f.uri,
            } for f in files])
        else:
            if not files:
                console.print("[dim]No files uploaded[/dim]")
                return

            from rich.table import Table
            table = Table(title="Uploaded Files")
            table.add_column("Name", style="cyan")
            table.add_column("Display Name")
            table.add_column("Type")

            for f in files:
                table.add_row(f.name, f.display_name, f.mime_type)

            console.print(table)

    except Exception as e:
        print_error(f"Failed to list files: {e}")
        raise typer.Exit(1)


@app.command("delete-file")
def delete_file(
    name: str = typer.Argument(..., help="File name to delete"),
):
    """
    Delete an uploaded file.

    Example: llm gemini delete-file files/abc123
    """
    try:
        provider = GeminiProvider()
        provider.delete_file(name)
        console.print(f"[green]Deleted: {name}[/green]")

    except Exception as e:
        print_error(f"Delete failed: {e}")
        raise typer.Exit(1)


# =========================================================================
# Utility Commands
# =========================================================================

@app.command("models")
def models(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List available Gemini models.

    Example: llm gemini models
    """
    try:
        provider = GeminiProvider()
        model_list = provider.list_models()

        if json_output:
            print_json(model_list)
        else:
            from rich.table import Table
            table = Table(title="Gemini Models")
            table.add_column("Name", style="cyan")
            table.add_column("Display Name")
            table.add_column("Methods", style="dim")

            for m in model_list:
                methods = ", ".join(m.get("supported_generation_methods", [])[:3])
                if len(m.get("supported_generation_methods", [])) > 3:
                    methods += "..."
                table.add_row(
                    m["name"].replace("models/", ""),
                    m.get("display_name", ""),
                    methods,
                )

            console.print(table)

    except Exception as e:
        print_error(f"Failed to list models: {e}")
        raise typer.Exit(1)
