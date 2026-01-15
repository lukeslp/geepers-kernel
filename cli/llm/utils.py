"""
Shared utilities for LLM CLI.

MIME type detection, progress bars, output formatting, and common helpers.

Author: Luke Steuber
"""

import os
import sys
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Union, Iterator, Any
from dataclasses import dataclass

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax

console = Console()


# =============================================================================
# MIME Type Detection
# =============================================================================

# Image MIME types
IMAGE_MIMES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}

# Audio MIME types
AUDIO_MIMES = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".aiff": "audio/aiff",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".wma": "audio/x-ms-wma",
}

# Video MIME types
VIDEO_MIMES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
}

# Document MIME types
DOCUMENT_MIMES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".json": "application/json",
    ".xml": "application/xml",
}


def detect_mime_type(path: Union[str, Path]) -> str:
    """Detect MIME type from file extension."""
    path = Path(path)
    ext = path.suffix.lower()

    # Check our known types first
    for type_map in [IMAGE_MIMES, AUDIO_MIMES, VIDEO_MIMES, DOCUMENT_MIMES]:
        if ext in type_map:
            return type_map[ext]

    # Fall back to mimetypes module
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def is_image(path: Union[str, Path]) -> bool:
    """Check if file is an image."""
    return Path(path).suffix.lower() in IMAGE_MIMES


def is_audio(path: Union[str, Path]) -> bool:
    """Check if file is audio."""
    return Path(path).suffix.lower() in AUDIO_MIMES


def is_video(path: Union[str, Path]) -> bool:
    """Check if file is video."""
    return Path(path).suffix.lower() in VIDEO_MIMES


def is_document(path: Union[str, Path]) -> bool:
    """Check if file is a document."""
    return Path(path).suffix.lower() in DOCUMENT_MIMES


def detect_mime_from_bytes(data: bytes) -> str:
    """Detect MIME type from file bytes (magic number detection)."""
    # Check common magic numbers
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    elif data[:2] == b'\xff\xd8':
        return "image/jpeg"
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return "image/webp"
    elif data[:4] == b'%PDF':
        return "application/pdf"
    elif data[:4] == b'ID3' or data[:2] == b'\xff\xfb':
        return "audio/mp3"
    elif data[:4] == b'RIFF' and data[8:12] == b'WAVE':
        return "audio/wav"
    elif data[:4] == b'fLaC':
        return "audio/flac"
    elif data[:4] == b'\x00\x00\x00\x1c' or data[:4] == b'\x00\x00\x00\x20':
        return "video/mp4"

    return "application/octet-stream"


def detect_mime_from_base64(data: str) -> str:
    """Detect MIME type from base64 string prefix."""
    # Check base64 header prefixes
    if data.startswith('/9j/'):
        return "image/jpeg"
    elif data.startswith('iVBOR'):
        return "image/png"
    elif data.startswith('R0lGOD'):
        return "image/gif"
    elif data.startswith('UklGR'):
        return "image/webp"
    elif data.startswith('JVBERi'):
        return "application/pdf"

    return "application/octet-stream"


# =============================================================================
# File Handling
# =============================================================================

def read_file_as_base64(path: Union[str, Path]) -> str:
    """Read file and return base64 encoded string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def read_file_bytes(path: Union[str, Path]) -> bytes:
    """Read file as bytes."""
    with open(path, "rb") as f:
        return f.read()


def get_file_size(path: Union[str, Path]) -> int:
    """Get file size in bytes."""
    return Path(path).stat().st_size


def get_file_size_mb(path: Union[str, Path]) -> float:
    """Get file size in megabytes."""
    return get_file_size(path) / (1024 * 1024)


def should_use_files_api(path: Union[str, Path], threshold_mb: float = 20.0) -> bool:
    """Check if file should be uploaded via Files API (>20MB)."""
    return get_file_size_mb(path) > threshold_mb


# =============================================================================
# Output Formatting
# =============================================================================

def print_response(
    content: str,
    title: Optional[str] = None,
    style: str = "default",
    as_markdown: bool = True,
):
    """Print a response with optional formatting."""
    if as_markdown:
        md = Markdown(content)
        if title:
            console.print(Panel(md, title=title, border_style="green"))
        else:
            console.print(md)
    else:
        if title:
            console.print(Panel(content, title=title, border_style="green"))
        else:
            console.print(content)


def print_error(message: str, hint: Optional[str] = None):
    """Print an error message."""
    console.print(f"[red bold]Error:[/red bold] {message}")
    if hint:
        console.print(f"[dim]Hint: {hint}[/dim]")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")


def print_success(message: str):
    """Print a success message."""
    console.print(f"[green]{message}[/green]")


def print_info(message: str):
    """Print an info message."""
    console.print(f"[cyan]{message}[/cyan]")


def print_json(data: Any):
    """Print data as formatted JSON."""
    import json
    console.print(Syntax(json.dumps(data, indent=2), "json"))


def stream_print(text_iterator: Iterator[str]):
    """Print streaming text as it arrives."""
    for chunk in text_iterator:
        console.print(chunk, end="")
    console.print()  # Final newline


# =============================================================================
# Progress Indicators
# =============================================================================

def create_spinner(description: str = "Processing..."):
    """Create a spinner progress indicator."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


def create_progress_bar(description: str = "Uploading..."):
    """Create a progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    )


# =============================================================================
# Provider Selection
# =============================================================================

@dataclass
class ProviderCapability:
    """Represents a provider's capabilities."""
    text: bool = True
    vision: bool = False
    audio: bool = False
    video: bool = False
    image_gen: bool = False
    tts: bool = False
    embedding: bool = False


def select_provider_for_capability(
    capability: str,
    preferred: Optional[str] = None,
    available_providers: Optional[dict] = None,
) -> Optional[str]:
    """
    Select the best provider for a given capability.

    Args:
        capability: The capability needed (text, vision, audio, video, etc.)
        preferred: Preferred provider (if available and capable)
        available_providers: Dict of provider info

    Returns:
        Provider name or None if no suitable provider found
    """
    from .providers import PROVIDERS, get_available_providers
    from .config import get_config

    config = get_config()
    providers = available_providers or PROVIDERS

    # Get providers that have API keys configured
    available = get_available_providers()

    # If preferred provider is available and capable, use it
    if preferred and preferred != "auto":
        if preferred in available and providers.get(preferred, {}).get(capability):
            return preferred
        elif preferred not in available:
            print_warning(f"Provider '{preferred}' not available (no API key)")
        elif not providers.get(preferred, {}).get(capability):
            print_warning(f"Provider '{preferred}' doesn't support {capability}")

    # Otherwise, find first available provider with capability
    # Prioritize by capability strength
    priority_order = {
        "text": ["gemini", "openai", "anthropic", "xai", "mistral", "cohere", "perplexity"],
        "vision": ["gemini", "openai", "anthropic", "xai", "mistral"],
        "audio": ["gemini", "openai"],
        "video": ["gemini"],
        "image_gen": ["openai", "xai", "gemini"],
        "tts": ["openai", "gemini"],
        "embedding": ["openai", "gemini", "cohere", "mistral"],
    }

    for provider in priority_order.get(capability, list(providers.keys())):
        if provider in available and providers.get(provider, {}).get(capability):
            return provider

    return None


# =============================================================================
# Interactive Helpers
# =============================================================================

def confirm(message: str, default: bool = False) -> bool:
    """Ask for confirmation."""
    from rich.prompt import Confirm
    return Confirm.ask(message, default=default)


def prompt(message: str, default: Optional[str] = None) -> str:
    """Prompt for input."""
    from rich.prompt import Prompt
    return Prompt.ask(message, default=default)
