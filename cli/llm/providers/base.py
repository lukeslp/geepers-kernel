"""
Base Provider Abstract Class

Defines the interface that all LLM providers must implement.

Author: Luke Steuber
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Iterator, AsyncIterator, Union
from pathlib import Path


@dataclass
class Capabilities:
    """Provider capability flags."""
    text: bool = True
    vision: bool = False
    audio: bool = False
    video: bool = False
    image_gen: bool = False
    tts: bool = False
    embedding: bool = False


@dataclass
class Message:
    """A chat message."""
    role: str  # "user", "assistant", "system"
    content: str
    images: Optional[List[Union[str, Path, bytes]]] = None  # Image paths, URLs, or bytes
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CompletionResponse:
    """Response from a completion request."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None  # {"prompt_tokens": x, "completion_tokens": y}
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingResponse:
    """Response from an embedding request."""
    embedding: List[float]
    model: str
    usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ImageResponse:
    """Response from an image generation request."""
    images: List[bytes]  # Raw image bytes
    model: str
    revised_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AudioResponse:
    """Response from a TTS or audio processing request."""
    audio: bytes  # Raw audio bytes
    model: str
    format: str = "mp3"
    metadata: Optional[Dict[str, Any]] = None


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement at minimum:
    - chat() for text generation
    - chat_stream() for streaming text generation

    Optional methods based on capabilities:
    - analyze_image() for vision
    - analyze_audio() for audio understanding
    - analyze_video() for video understanding
    - generate_image() for image generation
    - generate_speech() for TTS
    - embed() for embeddings
    """

    name: str
    capabilities: Capabilities
    env_key: str
    default_model: str

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the provider.

        Args:
            api_key: API key (falls back to environment variable)
            model: Model to use (falls back to default)
        """
        import os
        self.api_key = api_key or os.getenv(self.env_key)
        self.model = model or self.default_model

        if not self.api_key:
            raise ValueError(f"No API key found. Set {self.env_key} environment variable.")

    def supports(self, capability: str) -> bool:
        """Check if provider supports a capability."""
        return getattr(self.capabilities, capability, False)

    # =========================================================================
    # Required Methods (all providers must implement)
    # =========================================================================

    @abstractmethod
    def chat(
        self,
        messages: Union[str, List[Message]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> CompletionResponse:
        """
        Generate a chat completion.

        Args:
            messages: Single prompt string or list of Message objects
            model: Model to use (defaults to provider default)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific options

        Returns:
            CompletionResponse with generated text
        """
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: Union[str, List[Message]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> Iterator[str]:
        """
        Generate a streaming chat completion.

        Args:
            messages: Single prompt string or list of Message objects
            model: Model to use (defaults to provider default)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific options

        Yields:
            Text chunks as they are generated
        """
        pass

    # =========================================================================
    # Optional Methods (implement based on capabilities)
    # =========================================================================

    def analyze_image(
        self,
        image: Union[str, Path, bytes],
        prompt: str = "Describe this image in detail",
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Analyze an image with the LLM.

        Args:
            image: Image path, URL, or bytes
            prompt: Analysis prompt
            model: Model to use
            **kwargs: Additional options

        Returns:
            CompletionResponse with analysis
        """
        raise NotImplementedError(f"{self.name} does not support vision")

    def analyze_audio(
        self,
        audio: Union[str, Path, bytes],
        prompt: str = "Transcribe this audio",
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Analyze or transcribe audio.

        Args:
            audio: Audio path or bytes
            prompt: Analysis prompt
            model: Model to use
            **kwargs: Additional options

        Returns:
            CompletionResponse with transcription/analysis
        """
        raise NotImplementedError(f"{self.name} does not support audio")

    def analyze_video(
        self,
        video: Union[str, Path],
        prompt: str = "Describe this video",
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Analyze a video.

        Args:
            video: Video path or URL
            prompt: Analysis prompt
            model: Model to use
            **kwargs: Additional options

        Returns:
            CompletionResponse with analysis
        """
        raise NotImplementedError(f"{self.name} does not support video")

    def analyze_document(
        self,
        document: Union[str, Path, bytes],
        prompt: str = "Summarize this document",
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Analyze a document (PDF, etc.).

        Args:
            document: Document path or bytes
            prompt: Analysis prompt
            model: Model to use
            **kwargs: Additional options

        Returns:
            CompletionResponse with analysis
        """
        raise NotImplementedError(f"{self.name} does not support document analysis")

    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        n: int = 1,
        **kwargs,
    ) -> ImageResponse:
        """
        Generate an image from a prompt.

        Args:
            prompt: Image generation prompt
            model: Model to use
            size: Image size
            n: Number of images to generate
            **kwargs: Additional options

        Returns:
            ImageResponse with generated images
        """
        raise NotImplementedError(f"{self.name} does not support image generation")

    def generate_speech(
        self,
        text: str,
        model: Optional[str] = None,
        voice: Optional[str] = None,
        **kwargs,
    ) -> AudioResponse:
        """
        Generate speech from text (TTS).

        Args:
            text: Text to convert to speech
            model: Model to use
            voice: Voice to use
            **kwargs: Additional options

        Returns:
            AudioResponse with audio bytes
        """
        raise NotImplementedError(f"{self.name} does not support text-to-speech")

    def embed(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs,
    ) -> Union[EmbeddingResponse, List[EmbeddingResponse]]:
        """
        Generate embeddings for text.

        Args:
            text: Text or list of texts to embed
            model: Model to use
            **kwargs: Additional options

        Returns:
            EmbeddingResponse or list of EmbeddingResponse
        """
        raise NotImplementedError(f"{self.name} does not support embeddings")

    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.

        Returns:
            List of model info dicts
        """
        return [{"name": self.default_model, "description": "Default model"}]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _normalize_messages(self, messages: Union[str, List[Message]]) -> List[Message]:
        """Convert string prompt to message list."""
        if isinstance(messages, str):
            return [Message(role="user", content=messages)]
        return messages

    def _read_file_bytes(self, path: Union[str, Path]) -> bytes:
        """Read file as bytes."""
        with open(path, "rb") as f:
            return f.read()

    def _encode_base64(self, data: bytes) -> str:
        """Encode bytes as base64."""
        import base64
        return base64.b64encode(data).decode("utf-8")


__all__ = [
    "BaseProvider",
    "Capabilities",
    "Message",
    "CompletionResponse",
    "EmbeddingResponse",
    "ImageResponse",
    "AudioResponse",
]
