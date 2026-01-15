"""
Mistral Provider Implementation.

Client for Mistral AI models.

Author: Luke Steuber
"""

import os
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterator, Union

try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False

from ..base import (
    BaseProvider,
    Capabilities,
    Message,
    CompletionResponse,
    EmbeddingResponse,
)


class MistralProvider(BaseProvider):
    """
    Mistral AI Provider.

    Supports:
    - Text generation (Mistral Large, Medium, Small)
    - Vision (Pixtral)
    - Embeddings
    """

    name = "mistral"
    env_key = "MISTRAL_API_KEY"
    default_model = "mistral-large-latest"

    capabilities = Capabilities(
        text=True,
        vision=True,
        audio=False,
        video=False,
        image_gen=False,
        tts=False,
        embedding=True,
    )

    # Model constants
    DEFAULT_CHAT_MODEL = "mistral-large-latest"
    DEFAULT_VISION_MODEL = "pixtral-large-latest"
    DEFAULT_EMBED_MODEL = "mistral-embed"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Mistral provider.

        Args:
            api_key: Mistral API key (falls back to MISTRAL_API_KEY env var)
            model: Default model to use
        """
        if not MISTRAL_AVAILABLE:
            raise ImportError(
                "mistralai package not installed. "
                "Install with: pip install mistralai"
            )

        self.api_key = api_key or os.getenv(self.env_key)
        if not self.api_key:
            raise ValueError(f"No API key found. Set {self.env_key} environment variable.")

        self.model = model or self.default_model
        self.client = Mistral(api_key=self.api_key)

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
        Generate a chat completion with Mistral.

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

        mistral_messages = self._build_messages(messages)

        response = self.client.chat.complete(
            model=use_model,
            messages=mistral_messages,
            temperature=temperature,
            max_tokens=max_tokens,
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
        Stream a chat completion with Mistral.

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

        mistral_messages = self._build_messages(messages)

        stream = self.client.chat.stream(
            model=use_model,
            messages=mistral_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        for event in stream:
            if event.data.choices[0].delta.content:
                yield event.data.choices[0].delta.content

    # =========================================================================
    # Vision
    # =========================================================================

    def analyze_image(
        self,
        image: Union[str, Path, bytes],
        prompt: str = "Describe this image in detail",
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Analyze an image with Pixtral.

        Args:
            image: Image path, URL, or bytes
            prompt: Analysis prompt
            model: Model to use

        Returns:
            CompletionResponse with analysis
        """
        use_model = model or self.DEFAULT_VISION_MODEL

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

        response = self.client.chat.complete(
            model=use_model,
            messages=messages,
        )

        return CompletionResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            } if response.usage else None,
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
        Generate embeddings with Mistral.

        Args:
            text: Text or list of texts to embed
            model: Embedding model

        Returns:
            EmbeddingResponse or list of EmbeddingResponse
        """
        use_model = model or self.DEFAULT_EMBED_MODEL

        if isinstance(text, str):
            texts = [text]
        else:
            texts = text

        response = self.client.embeddings.create(
            model=use_model,
            inputs=texts,
        )

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
        """List available Mistral models."""
        return [
            {"name": "mistral-large-latest", "description": "Most capable", "context": 128000},
            {"name": "mistral-medium-latest", "description": "Balanced", "context": 32000},
            {"name": "mistral-small-latest", "description": "Fast", "context": 32000},
            {"name": "codestral-latest", "description": "Code specialized", "context": 32000},
            {"name": "pixtral-large-latest", "description": "Vision model", "context": 128000},
            {"name": "mistral-embed", "description": "Embeddings", "dimensions": 1024},
        ]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_messages(self, messages: List[Message]) -> List[Dict]:
        """Convert Message objects to Mistral format."""
        mistral_messages = []

        for msg in messages:
            content = msg.content

            if msg.images:
                content = [{"type": "text", "text": msg.content}]
                for img in msg.images:
                    content.append(self._prepare_image(img))

            mistral_messages.append({
                "role": msg.role,
                "content": content,
            })

        return mistral_messages

    def _prepare_image(self, image: Union[str, Path, bytes]) -> Dict:
        """Prepare image content for Mistral API."""
        if isinstance(image, str) and image.startswith(("http://", "https://")):
            return {"type": "image_url", "image_url": image}

        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Image not found: {path}")

            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")

            suffix = path.suffix.lower()
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
            mime_type = mime_map.get(suffix, "image/png")

            return {"type": "image_url", "image_url": f"data:{mime_type};base64,{data}"}

        if isinstance(image, bytes):
            data = base64.b64encode(image).decode("utf-8")
            return {"type": "image_url", "image_url": f"data:image/png;base64,{data}"}

        raise ValueError(f"Unsupported image type: {type(image)}")
