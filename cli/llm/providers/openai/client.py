"""
OpenAI Provider Implementation.

Comprehensive client for OpenAI's API including GPT-4, DALL-E, Whisper, and TTS.

Author: Luke Steuber
"""

import os
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterator, Union

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from ..base import (
    BaseProvider,
    Capabilities,
    Message,
    CompletionResponse,
    EmbeddingResponse,
    ImageResponse,
    AudioResponse,
)


class OpenAIProvider(BaseProvider):
    """
    OpenAI API Provider.

    Supports:
    - Text generation (GPT-4o, GPT-4, o1 series)
    - Vision (GPT-4o, GPT-4o-mini)
    - Audio transcription (Whisper)
    - Image generation (DALL-E 3, DALL-E 2)
    - Text-to-speech (TTS-1, TTS-1-HD)
    - Embeddings (text-embedding-3)
    """

    name = "openai"
    env_key = "OPENAI_API_KEY"
    default_model = "gpt-4o"

    capabilities = Capabilities(
        text=True,
        vision=True,
        audio=True,
        video=False,
        image_gen=True,
        tts=True,
        embedding=True,
    )

    # Model constants
    DEFAULT_CHAT_MODEL = "gpt-4o"
    DEFAULT_VISION_MODEL = "gpt-4o"
    DEFAULT_WHISPER_MODEL = "whisper-1"
    DEFAULT_DALLE_MODEL = "dall-e-3"
    DEFAULT_TTS_MODEL = "tts-1"
    DEFAULT_EMBED_MODEL = "text-embedding-3-small"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
            model: Default model to use
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        self.api_key = api_key or os.getenv(self.env_key)
        if not self.api_key:
            raise ValueError(f"No API key found. Set {self.env_key} environment variable.")

        self.model = model or self.default_model
        self.client = OpenAI(api_key=self.api_key)

    # =========================================================================
    # Text Generation
    # =========================================================================

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
            messages: Prompt string or list of Message objects
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            CompletionResponse with generated text
        """
        use_model = model or self.model
        messages = self._normalize_messages(messages)

        # Build OpenAI messages format
        openai_messages = self._build_messages(messages)

        response = self.client.chat.completions.create(
            model=use_model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        return CompletionResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            finish_reason=response.choices[0].finish_reason,
        )

    def chat_stream(
        self,
        messages: Union[str, List[Message]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> Iterator[str]:
        """
        Stream a chat completion.

        Args:
            messages: Prompt string or list of Message objects
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Yields:
            Text chunks as they are generated
        """
        use_model = model or self.model
        messages = self._normalize_messages(messages)

        openai_messages = self._build_messages(messages)

        stream = self.client.chat.completions.create(
            model=use_model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # =========================================================================
    # Vision (Image Analysis)
    # =========================================================================

    def analyze_image(
        self,
        image: Union[str, Path, bytes],
        prompt: str = "Describe this image in detail",
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Analyze an image with GPT-4 Vision.

        Args:
            image: Image path, URL, or bytes
            prompt: Analysis prompt
            model: Model to use

        Returns:
            CompletionResponse with analysis
        """
        use_model = model or self.DEFAULT_VISION_MODEL

        # Prepare image content
        image_content = self._prepare_image(image)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    image_content,
                ],
            }
        ]

        response = self.client.chat.completions.create(
            model=use_model,
            messages=messages,
            max_tokens=4096,
        )

        return CompletionResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
        )

    def analyze_images(
        self,
        images: List[Union[str, Path, bytes]],
        prompt: str = "Compare these images",
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Analyze multiple images.

        Args:
            images: List of image paths, URLs, or bytes
            prompt: Analysis prompt
            model: Model to use

        Returns:
            CompletionResponse with analysis
        """
        use_model = model or self.DEFAULT_VISION_MODEL

        content = [{"type": "text", "text": prompt}]
        for img in images:
            content.append(self._prepare_image(img))

        messages = [{"role": "user", "content": content}]

        response = self.client.chat.completions.create(
            model=use_model,
            messages=messages,
            max_tokens=4096,
        )

        return CompletionResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
        )

    # =========================================================================
    # Audio (Whisper Transcription)
    # =========================================================================

    def analyze_audio(
        self,
        audio: Union[str, Path, bytes],
        prompt: str = "Transcribe this audio",
        model: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Transcribe audio with Whisper.

        Args:
            audio: Audio path or bytes
            prompt: Optional prompt to guide transcription
            model: Model to use (whisper-1)
            language: ISO-639-1 language code

        Returns:
            CompletionResponse with transcription
        """
        use_model = model or self.DEFAULT_WHISPER_MODEL

        # Handle file path
        if isinstance(audio, (str, Path)):
            audio_file = open(audio, "rb")
        else:
            # For bytes, create a file-like object
            import io
            audio_file = io.BytesIO(audio)
            audio_file.name = "audio.mp3"

        try:
            transcription = self.client.audio.transcriptions.create(
                model=use_model,
                file=audio_file,
                prompt=prompt if prompt != "Transcribe this audio" else None,
                language=language,
            )

            return CompletionResponse(
                content=transcription.text,
                model=use_model,
            )
        finally:
            if isinstance(audio, (str, Path)):
                audio_file.close()

    def translate_audio(
        self,
        audio: Union[str, Path, bytes],
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Translate audio to English with Whisper.

        Args:
            audio: Audio path or bytes
            model: Model to use

        Returns:
            CompletionResponse with English translation
        """
        use_model = model or self.DEFAULT_WHISPER_MODEL

        if isinstance(audio, (str, Path)):
            audio_file = open(audio, "rb")
        else:
            import io
            audio_file = io.BytesIO(audio)
            audio_file.name = "audio.mp3"

        try:
            translation = self.client.audio.translations.create(
                model=use_model,
                file=audio_file,
            )

            return CompletionResponse(
                content=translation.text,
                model=use_model,
            )
        finally:
            if isinstance(audio, (str, Path)):
                audio_file.close()

    # =========================================================================
    # Image Generation (DALL-E)
    # =========================================================================

    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        n: int = 1,
        quality: str = "standard",
        style: str = "vivid",
        **kwargs,
    ) -> ImageResponse:
        """
        Generate images with DALL-E.

        Args:
            prompt: Image generation prompt
            model: Model (dall-e-3, dall-e-2)
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            n: Number of images (1 for DALL-E 3)
            quality: Image quality (standard, hd)
            style: Image style (vivid, natural)

        Returns:
            ImageResponse with generated images
        """
        use_model = model or self.DEFAULT_DALLE_MODEL

        # DALL-E 3 only supports n=1
        if use_model == "dall-e-3" and n > 1:
            n = 1

        response = self.client.images.generate(
            model=use_model,
            prompt=prompt,
            size=size,
            n=n,
            quality=quality,
            style=style,
            response_format="b64_json",
        )

        images = []
        for data in response.data:
            images.append(base64.b64decode(data.b64_json))

        return ImageResponse(
            images=images,
            model=use_model,
            revised_prompt=response.data[0].revised_prompt if response.data else None,
        )

    # =========================================================================
    # Text-to-Speech
    # =========================================================================

    def generate_speech(
        self,
        text: str,
        model: Optional[str] = None,
        voice: Optional[str] = None,
        speed: float = 1.0,
        response_format: str = "mp3",
        **kwargs,
    ) -> AudioResponse:
        """
        Generate speech from text.

        Args:
            text: Text to convert to speech
            model: Model (tts-1, tts-1-hd)
            voice: Voice (alloy, echo, fable, onyx, nova, shimmer)
            speed: Speed (0.25 to 4.0)
            response_format: Output format (mp3, opus, aac, flac)

        Returns:
            AudioResponse with audio bytes
        """
        use_model = model or self.DEFAULT_TTS_MODEL
        use_voice = voice or "alloy"

        response = self.client.audio.speech.create(
            model=use_model,
            voice=use_voice,
            input=text,
            speed=speed,
            response_format=response_format,
        )

        return AudioResponse(
            audio=response.content,
            model=use_model,
            format=response_format,
        )

    # =========================================================================
    # Embeddings
    # =========================================================================

    def embed(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        **kwargs,
    ) -> Union[EmbeddingResponse, List[EmbeddingResponse]]:
        """
        Generate embeddings for text.

        Args:
            text: Text or list of texts to embed
            model: Embedding model
            dimensions: Output dimensions (for text-embedding-3 models)

        Returns:
            EmbeddingResponse or list of EmbeddingResponse
        """
        use_model = model or self.DEFAULT_EMBED_MODEL

        # Build request
        request_kwargs = {"model": use_model, "input": text}
        if dimensions and "text-embedding-3" in use_model:
            request_kwargs["dimensions"] = dimensions

        response = self.client.embeddings.create(**request_kwargs)

        if isinstance(text, str):
            return EmbeddingResponse(
                embedding=response.data[0].embedding,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None,
            )
        else:
            return [
                EmbeddingResponse(
                    embedding=data.embedding,
                    model=response.model,
                )
                for data in response.data
            ]

    # =========================================================================
    # Model Listing
    # =========================================================================

    def list_models(self) -> List[Dict[str, Any]]:
        """List available OpenAI models."""
        models = []
        for model in self.client.models.list():
            models.append({
                "name": model.id,
                "created": model.created,
                "owned_by": model.owned_by,
            })
        return models

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_messages(self, messages: List[Message]) -> List[Dict]:
        """Convert Message objects to OpenAI format."""
        openai_messages = []

        for msg in messages:
            content = msg.content

            # Handle images in message
            if msg.images:
                content = [{"type": "text", "text": msg.content}]
                for img in msg.images:
                    content.append(self._prepare_image(img))

            openai_messages.append({
                "role": msg.role,
                "content": content,
            })

        return openai_messages

    def _prepare_image(self, image: Union[str, Path, bytes]) -> Dict:
        """
        Prepare image content for OpenAI API.

        Args:
            image: Image path, URL, or bytes

        Returns:
            Image content dict for API
        """
        # Handle URLs
        if isinstance(image, str) and image.startswith(("http://", "https://")):
            return {
                "type": "image_url",
                "image_url": {"url": image},
            }

        # Handle file paths
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Image not found: {path}")

            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")

            # Detect MIME type
            suffix = path.suffix.lower()
            mime_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_map.get(suffix, "image/png")

            return {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{data}"},
            }

        # Handle bytes
        if isinstance(image, bytes):
            data = base64.b64encode(image).decode("utf-8")
            # Try to detect MIME type
            if image.startswith(b"\x89PNG"):
                mime_type = "image/png"
            elif image.startswith(b"\xff\xd8\xff"):
                mime_type = "image/jpeg"
            else:
                mime_type = "image/png"

            return {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{data}"},
            }

        raise ValueError(f"Unsupported image type: {type(image)}")
