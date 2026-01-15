"""
xAI Provider Implementation.

Client for Grok models using OpenAI-compatible API.

Author: Luke Steuber
"""

import os
import base64
import requests
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
    ImageResponse,
)


class XAIProvider(BaseProvider):
    """
    xAI Grok API Provider.

    Uses OpenAI-compatible API with xAI base URL.

    Supports:
    - Text generation (Grok-3, Grok-3-fast, Grok-2)
    - Vision (Grok-2-vision)
    - Image generation (Aurora)
    """

    name = "xai"
    env_key = "XAI_API_KEY"
    default_model = "grok-3"

    capabilities = Capabilities(
        text=True,
        vision=True,
        audio=False,
        video=False,
        image_gen=True,
        tts=False,
        embedding=False,
    )

    # API endpoints
    BASE_URL = "https://api.x.ai/v1"

    # Model constants
    DEFAULT_CHAT_MODEL = "grok-3"
    DEFAULT_VISION_MODEL = "grok-2-vision"
    DEFAULT_IMAGE_MODEL = "aurora"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize xAI provider.

        Args:
            api_key: xAI API key (falls back to XAI_API_KEY env var)
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

        # xAI uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.BASE_URL,
        )

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
        Generate a chat completion with Grok.

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
        Stream a chat completion with Grok.

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
        Analyze an image with Grok Vision.

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
        Analyze multiple images with Grok Vision.

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
            } if response.usage else None,
        )

    # =========================================================================
    # Image Generation (Aurora)
    # =========================================================================

    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        n: int = 1,
        **kwargs,
    ) -> ImageResponse:
        """
        Generate images with Aurora.

        Args:
            prompt: Image generation prompt
            model: Model to use (aurora)
            size: Image size
            n: Number of images

        Returns:
            ImageResponse with generated images
        """
        use_model = model or self.DEFAULT_IMAGE_MODEL

        # Aurora uses direct API call
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": use_model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "response_format": "b64_json",
        }

        response = requests.post(
            f"{self.BASE_URL}/images/generations",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

        data = response.json()

        images = []
        for item in data.get("data", []):
            if "b64_json" in item:
                images.append(base64.b64decode(item["b64_json"]))

        return ImageResponse(
            images=images,
            model=use_model,
            revised_prompt=data.get("data", [{}])[0].get("revised_prompt"),
        )

    # =========================================================================
    # Model Listing
    # =========================================================================

    def list_models(self) -> List[Dict[str, Any]]:
        """List available xAI models."""
        return [
            {
                "name": "grok-3",
                "description": "Latest Grok model",
                "context_window": 128000,
            },
            {
                "name": "grok-3-fast",
                "description": "Fast Grok model",
                "context_window": 128000,
            },
            {
                "name": "grok-2",
                "description": "Grok 2",
                "context_window": 128000,
            },
            {
                "name": "grok-2-vision",
                "description": "Grok 2 with vision",
                "context_window": 32000,
            },
            {
                "name": "aurora",
                "description": "Aurora image generation",
            },
        ]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_messages(self, messages: List[Message]) -> List[Dict]:
        """Convert Message objects to OpenAI format."""
        openai_messages = []

        for msg in messages:
            content = msg.content

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
        Prepare image content for xAI API.

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
