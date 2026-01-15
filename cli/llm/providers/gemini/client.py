"""
Gemini Provider Implementation.

Comprehensive client for Google's Gemini API supporting all modalities.

Author: Luke Steuber
"""

import os
import mimetypes
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterator, Union

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from ..base import (
    BaseProvider,
    Capabilities,
    Message,
    CompletionResponse,
    EmbeddingResponse,
    ImageResponse,
    AudioResponse,
)


class GeminiProvider(BaseProvider):
    """
    Google Gemini API Provider.

    Supports the full range of Gemini capabilities:
    - Text generation with streaming
    - Vision (image analysis)
    - Audio (transcription and analysis)
    - Video (up to 6 hours with 2M context)
    - Document processing (PDF up to 50MB)
    - Image generation (Imagen)
    - Text-to-speech
    - Embeddings
    """

    name = "gemini"
    env_key = "GEMINI_API_KEY"
    default_model = "gemini-2.5-flash"

    capabilities = Capabilities(
        text=True,
        vision=True,
        audio=True,
        video=True,
        image_gen=True,
        tts=True,
        embedding=True,
    )

    # Model constants
    DEFAULT_CHAT_MODEL = "gemini-2.5-flash"
    DEFAULT_VISION_MODEL = "gemini-2.5-flash"
    DEFAULT_AUDIO_MODEL = "gemini-2.5-flash"
    DEFAULT_VIDEO_MODEL = "gemini-2.5-flash"
    DEFAULT_IMAGE_MODEL = "imagen-4.0-generate-001"
    DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"
    DEFAULT_EMBED_MODEL = "text-embedding-004"

    # File size thresholds
    INLINE_MAX_SIZE = 20 * 1024 * 1024  # 20MB

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini provider.

        Args:
            api_key: Gemini API key (falls back to GEMINI_API_KEY env var)
            model: Default model to use
        """
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )

        self.api_key = api_key or os.getenv(self.env_key)
        if not self.api_key:
            raise ValueError(f"No API key found. Set {self.env_key} environment variable.")

        self.model = model or self.default_model

        # Configure the SDK
        genai.configure(api_key=self.api_key)

        # Safety settings (permissive for analysis tasks)
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

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
            **kwargs: Additional generation config

        Returns:
            CompletionResponse with generated text
        """
        use_model = model or self.model
        messages = self._normalize_messages(messages)

        # Build contents for Gemini
        contents = self._build_contents(messages)

        # Create model instance
        gen_model = genai.GenerativeModel(
            model_name=use_model,
            safety_settings=self.safety_settings,
        )

        # Generation config
        gen_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            **kwargs,
        )

        # Generate
        response = gen_model.generate_content(
            contents,
            generation_config=gen_config,
        )

        return CompletionResponse(
            content=response.text,
            model=use_model,
            usage=self._extract_usage(response),
            finish_reason=self._get_finish_reason(response),
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

        contents = self._build_contents(messages)

        gen_model = genai.GenerativeModel(
            model_name=use_model,
            safety_settings=self.safety_settings,
        )

        gen_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = gen_model.generate_content(
            contents,
            generation_config=gen_config,
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

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
        Analyze an image with Gemini.

        Args:
            image: Image path, URL, or bytes
            prompt: Analysis prompt
            model: Model to use (defaults to vision model)

        Returns:
            CompletionResponse with analysis
        """
        use_model = model or self.DEFAULT_VISION_MODEL

        # Prepare image content
        image_part = self._prepare_media(image)

        gen_model = genai.GenerativeModel(
            model_name=use_model,
            safety_settings=self.safety_settings,
        )

        response = gen_model.generate_content([prompt, image_part])

        return CompletionResponse(
            content=response.text,
            model=use_model,
            usage=self._extract_usage(response),
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

        # Prepare all images
        parts = [prompt]
        for img in images:
            parts.append(self._prepare_media(img))

        gen_model = genai.GenerativeModel(
            model_name=use_model,
            safety_settings=self.safety_settings,
        )

        response = gen_model.generate_content(parts)

        return CompletionResponse(
            content=response.text,
            model=use_model,
            usage=self._extract_usage(response),
        )

    # =========================================================================
    # Audio Analysis
    # =========================================================================

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
            prompt: Analysis prompt (e.g., "Transcribe", "Summarize", "Translate")
            model: Model to use

        Returns:
            CompletionResponse with transcription/analysis
        """
        use_model = model or self.DEFAULT_AUDIO_MODEL

        # Prepare audio content
        audio_part = self._prepare_media(audio)

        gen_model = genai.GenerativeModel(
            model_name=use_model,
            safety_settings=self.safety_settings,
        )

        response = gen_model.generate_content([prompt, audio_part])

        return CompletionResponse(
            content=response.text,
            model=use_model,
            usage=self._extract_usage(response),
        )

    # =========================================================================
    # Video Analysis
    # =========================================================================

    def analyze_video(
        self,
        video: Union[str, Path],
        prompt: str = "Describe this video",
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Analyze a video.

        Supports videos up to 6 hours with Gemini's 2M token context.

        Args:
            video: Video path or URL
            prompt: Analysis prompt
            model: Model to use

        Returns:
            CompletionResponse with analysis
        """
        use_model = model or self.DEFAULT_VIDEO_MODEL

        # Videos typically need Files API due to size
        video_part = self._prepare_media(video, force_upload=True)

        gen_model = genai.GenerativeModel(
            model_name=use_model,
            safety_settings=self.safety_settings,
        )

        response = gen_model.generate_content([prompt, video_part])

        return CompletionResponse(
            content=response.text,
            model=use_model,
            usage=self._extract_usage(response),
        )

    # =========================================================================
    # Document Processing
    # =========================================================================

    def analyze_document(
        self,
        document: Union[str, Path, bytes],
        prompt: str = "Summarize this document",
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Analyze a document (PDF, etc.).

        Supports PDFs up to 50MB and 1000 pages.

        Args:
            document: Document path or bytes
            prompt: Analysis prompt
            model: Model to use

        Returns:
            CompletionResponse with analysis
        """
        use_model = model or self.DEFAULT_VISION_MODEL

        # Prepare document
        doc_part = self._prepare_media(document)

        gen_model = genai.GenerativeModel(
            model_name=use_model,
            safety_settings=self.safety_settings,
        )

        response = gen_model.generate_content([prompt, doc_part])

        return CompletionResponse(
            content=response.text,
            model=use_model,
            usage=self._extract_usage(response),
        )

    # =========================================================================
    # Image Generation (Imagen)
    # =========================================================================

    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        n: int = 1,
        aspect_ratio: Optional[str] = None,
        **kwargs,
    ) -> ImageResponse:
        """
        Generate images using Imagen.

        Args:
            prompt: Image generation prompt
            model: Model to use (defaults to Imagen)
            size: Image size (e.g., "1024x1024")
            n: Number of images to generate
            aspect_ratio: Aspect ratio (e.g., "16:9", "1:1", "9:16")

        Returns:
            ImageResponse with generated images
        """
        use_model = model or self.DEFAULT_IMAGE_MODEL

        # Imagen uses a different API pattern
        imagen = genai.ImageGenerationModel(use_model)

        # Parse aspect ratio from size if not provided
        if not aspect_ratio and size:
            width, height = map(int, size.split("x"))
            if width > height:
                aspect_ratio = "16:9"
            elif height > width:
                aspect_ratio = "9:16"
            else:
                aspect_ratio = "1:1"

        response = imagen.generate_images(
            prompt=prompt,
            number_of_images=n,
            aspect_ratio=aspect_ratio or "1:1",
            **kwargs,
        )

        # Extract image bytes
        images = []
        for img in response.images:
            images.append(img._pil_image.tobytes() if hasattr(img, '_pil_image') else img.data)

        return ImageResponse(
            images=images,
            model=use_model,
            revised_prompt=None,
        )

    # =========================================================================
    # Text-to-Speech
    # =========================================================================

    def generate_speech(
        self,
        text: str,
        model: Optional[str] = None,
        voice: Optional[str] = None,
        **kwargs,
    ) -> AudioResponse:
        """
        Generate speech from text using Gemini TTS.

        Args:
            text: Text to convert to speech
            model: TTS model to use
            voice: Voice to use (e.g., "Puck", "Charon", "Kore", etc.)

        Returns:
            AudioResponse with audio bytes
        """
        use_model = model or self.DEFAULT_TTS_MODEL

        gen_model = genai.GenerativeModel(use_model)

        # Build TTS config
        config = {
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": voice or "Puck"
                    }
                }
            }
        }

        response = gen_model.generate_content(
            text,
            generation_config=config,
        )

        # Extract audio data
        audio_data = b""
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data.mime_type.startswith("audio"):
                audio_data = part.inline_data.data

        return AudioResponse(
            audio=audio_data,
            model=use_model,
            format="wav",
        )

    # =========================================================================
    # Embeddings
    # =========================================================================

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
            model: Embedding model to use

        Returns:
            EmbeddingResponse or list of EmbeddingResponse
        """
        use_model = model or self.DEFAULT_EMBED_MODEL

        if isinstance(text, str):
            result = genai.embed_content(
                model=use_model,
                content=text,
            )
            return EmbeddingResponse(
                embedding=result["embedding"],
                model=use_model,
            )
        else:
            # Batch embedding
            results = []
            for t in text:
                result = genai.embed_content(
                    model=use_model,
                    content=t,
                )
                results.append(EmbeddingResponse(
                    embedding=result["embedding"],
                    model=use_model,
                ))
            return results

    # =========================================================================
    # Files API
    # =========================================================================

    def upload_file(self, path: Union[str, Path], display_name: Optional[str] = None) -> Any:
        """
        Upload a file to Gemini Files API.

        Args:
            path: Path to file
            display_name: Optional display name

        Returns:
            Uploaded file object
        """
        path = Path(path)
        return genai.upload_file(
            path=str(path),
            display_name=display_name or path.name,
        )

    def list_files(self) -> List[Any]:
        """List uploaded files."""
        return list(genai.list_files())

    def delete_file(self, file_name: str):
        """Delete an uploaded file."""
        genai.delete_file(file_name)

    def get_file(self, file_name: str) -> Any:
        """Get file metadata."""
        return genai.get_file(file_name)

    # =========================================================================
    # Model Listing
    # =========================================================================

    def list_models(self) -> List[Dict[str, Any]]:
        """List available Gemini models."""
        models = []
        for model in genai.list_models():
            models.append({
                "name": model.name,
                "display_name": model.display_name,
                "description": model.description,
                "supported_generation_methods": model.supported_generation_methods,
            })
        return models

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_contents(self, messages: List[Message]) -> List[Dict]:
        """Convert Message objects to Gemini content format."""
        contents = []

        for msg in messages:
            role = "user" if msg.role == "user" else "model"

            parts = []
            if msg.content:
                parts.append({"text": msg.content})

            # Add any images
            if msg.images:
                for img in msg.images:
                    parts.append(self._prepare_media(img))

            contents.append({
                "role": role,
                "parts": parts,
            })

        return contents

    def _prepare_media(
        self,
        media: Union[str, Path, bytes],
        force_upload: bool = False,
    ) -> Dict:
        """
        Prepare media content for Gemini API.

        Handles:
        - File paths (auto-detects MIME type)
        - URLs (for web images)
        - Raw bytes (with MIME detection)
        - Large files (uploads to Files API)

        Args:
            media: Media to prepare
            force_upload: Force upload to Files API

        Returns:
            Content part dict for Gemini API
        """
        # Handle URLs
        if isinstance(media, str) and media.startswith(("http://", "https://")):
            return {"file_uri": media}

        # Handle file paths
        if isinstance(media, (str, Path)):
            path = Path(media)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            # Get MIME type
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type:
                mime_type = "application/octet-stream"

            # Check size for upload decision
            file_size = path.stat().st_size

            if force_upload or file_size > self.INLINE_MAX_SIZE:
                # Upload to Files API
                uploaded = self.upload_file(path)
                return {"file_data": {"file_uri": uploaded.uri, "mime_type": mime_type}}
            else:
                # Inline as base64
                with open(path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                return {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": data,
                    }
                }

        # Handle raw bytes
        if isinstance(media, bytes):
            # Try to detect MIME type from magic bytes
            mime_type = self._detect_mime_from_bytes(media)
            data = base64.b64encode(media).decode("utf-8")
            return {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": data,
                }
            }

        raise ValueError(f"Unsupported media type: {type(media)}")

    def _detect_mime_from_bytes(self, data: bytes) -> str:
        """Detect MIME type from magic bytes."""
        # Common magic bytes
        if data.startswith(b"\x89PNG"):
            return "image/png"
        elif data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif data.startswith(b"GIF8"):
            return "image/gif"
        elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"
        elif data.startswith(b"%PDF"):
            return "application/pdf"
        elif data.startswith(b"ID3") or data.startswith(b"\xff\xfb"):
            return "audio/mpeg"
        elif data.startswith(b"RIFF") and data[8:12] == b"WAVE":
            return "audio/wav"
        elif data.startswith(b"ftyp") or data[4:8] == b"ftyp":
            # Could be mp4 video or m4a audio
            return "video/mp4"
        else:
            return "application/octet-stream"

    def _extract_usage(self, response) -> Optional[Dict[str, int]]:
        """Extract token usage from response."""
        try:
            if hasattr(response, "usage_metadata"):
                meta = response.usage_metadata
                return {
                    "prompt_tokens": getattr(meta, "prompt_token_count", 0),
                    "completion_tokens": getattr(meta, "candidates_token_count", 0),
                    "total_tokens": getattr(meta, "total_token_count", 0),
                }
        except Exception:
            pass
        return None

    def _get_finish_reason(self, response) -> Optional[str]:
        """Extract finish reason from response."""
        try:
            if response.candidates:
                return str(response.candidates[0].finish_reason)
        except Exception:
            pass
        return None
