"""
Anthropic Provider Implementation.

Client for Claude models supporting text and vision.

Author: Luke Steuber
"""

import os
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterator, Union

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from ..base import (
    BaseProvider,
    Capabilities,
    Message,
    CompletionResponse,
)


class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude API Provider.

    Supports:
    - Text generation (Claude Sonnet 4, Opus 4, Claude 3.5)
    - Vision (all vision-capable Claude models)
    """

    name = "anthropic"
    env_key = "ANTHROPIC_API_KEY"
    default_model = "claude-sonnet-4-20250514"

    capabilities = Capabilities(
        text=True,
        vision=True,
        audio=False,
        video=False,
        image_gen=False,
        tts=False,
        embedding=False,
    )

    # Model constants
    DEFAULT_CHAT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_VISION_MODEL = "claude-sonnet-4-20250514"

    # Max tokens by model
    MODEL_MAX_TOKENS = {
        "claude-opus-4-20250514": 8192,
        "claude-sonnet-4-20250514": 8192,
        "claude-3-5-sonnet-20241022": 8192,
        "claude-3-5-haiku-20241022": 8192,
        "claude-3-opus-20240229": 4096,
        "claude-3-sonnet-20240229": 4096,
        "claude-3-haiku-20240307": 4096,
    }

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
            model: Default model to use
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        self.api_key = api_key or os.getenv(self.env_key)
        if not self.api_key:
            raise ValueError(f"No API key found. Set {self.env_key} environment variable.")

        self.model = model or self.default_model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    # =========================================================================
    # Text Generation
    # =========================================================================

    def chat(
        self,
        messages: Union[str, List[Message]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Generate a chat completion with Claude.

        Args:
            messages: Prompt string or list of Message objects
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            system: System prompt

        Returns:
            CompletionResponse with generated text
        """
        use_model = model or self.model
        messages = self._normalize_messages(messages)

        # Extract system message and build Anthropic format
        system_prompt, anthropic_messages = self._build_messages(messages)
        if system:
            system_prompt = system

        # Get appropriate max tokens for model
        model_max = self.MODEL_MAX_TOKENS.get(use_model, 4096)
        use_max_tokens = min(max_tokens, model_max)

        response = self.client.messages.create(
            model=use_model,
            messages=anthropic_messages,
            system=system_prompt or "",
            temperature=temperature,
            max_tokens=use_max_tokens,
            **kwargs,
        )

        # Extract text content
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return CompletionResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
        )

    def chat_stream(
        self,
        messages: Union[str, List[Message]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system: Optional[str] = None,
        **kwargs,
    ) -> Iterator[str]:
        """
        Stream a chat completion with Claude.

        Args:
            messages: Prompt string or list of Message objects
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            system: System prompt

        Yields:
            Text chunks as they are generated
        """
        use_model = model or self.model
        messages = self._normalize_messages(messages)

        system_prompt, anthropic_messages = self._build_messages(messages)
        if system:
            system_prompt = system

        model_max = self.MODEL_MAX_TOKENS.get(use_model, 4096)
        use_max_tokens = min(max_tokens, model_max)

        with self.client.messages.stream(
            model=use_model,
            messages=anthropic_messages,
            system=system_prompt or "",
            temperature=temperature,
            max_tokens=use_max_tokens,
            **kwargs,
        ) as stream:
            for text in stream.text_stream:
                yield text

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
        Analyze an image with Claude Vision.

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
                    image_content,
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        model_max = self.MODEL_MAX_TOKENS.get(use_model, 4096)

        response = self.client.messages.create(
            model=use_model,
            messages=messages,
            max_tokens=model_max,
        )

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return CompletionResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
        )

    def analyze_images(
        self,
        images: List[Union[str, Path, bytes]],
        prompt: str = "Compare these images",
        model: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Analyze multiple images with Claude Vision.

        Args:
            images: List of image paths, URLs, or bytes
            prompt: Analysis prompt
            model: Model to use

        Returns:
            CompletionResponse with analysis
        """
        use_model = model or self.DEFAULT_VISION_MODEL

        content = []
        for img in images:
            content.append(self._prepare_image(img))
        content.append({"type": "text", "text": prompt})

        messages = [{"role": "user", "content": content}]

        model_max = self.MODEL_MAX_TOKENS.get(use_model, 4096)

        response = self.client.messages.create(
            model=use_model,
            messages=messages,
            max_tokens=model_max,
        )

        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text

        return CompletionResponse(
            content=text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
        )

    # =========================================================================
    # Model Listing
    # =========================================================================

    def list_models(self) -> List[Dict[str, Any]]:
        """List available Claude models."""
        # Anthropic doesn't have a list models endpoint, so return known models
        return [
            {
                "name": "claude-opus-4-20250514",
                "description": "Most capable Claude model",
                "context_window": 200000,
            },
            {
                "name": "claude-sonnet-4-20250514",
                "description": "Balanced performance and speed",
                "context_window": 200000,
            },
            {
                "name": "claude-3-5-sonnet-20241022",
                "description": "Claude 3.5 Sonnet",
                "context_window": 200000,
            },
            {
                "name": "claude-3-5-haiku-20241022",
                "description": "Fast Claude 3.5",
                "context_window": 200000,
            },
            {
                "name": "claude-3-opus-20240229",
                "description": "Claude 3 Opus (legacy)",
                "context_window": 200000,
            },
            {
                "name": "claude-3-sonnet-20240229",
                "description": "Claude 3 Sonnet (legacy)",
                "context_window": 200000,
            },
            {
                "name": "claude-3-haiku-20240307",
                "description": "Claude 3 Haiku (legacy)",
                "context_window": 200000,
            },
        ]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_messages(self, messages: List[Message]) -> tuple:
        """
        Convert Message objects to Anthropic format.

        Returns:
            Tuple of (system_prompt, messages)
        """
        system_prompt = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
                continue

            content = []

            # Add images first if present
            if msg.images:
                for img in msg.images:
                    content.append(self._prepare_image(img))

            # Add text content
            if msg.content:
                content.append({"type": "text", "text": msg.content})

            # If content is just text, simplify
            if len(content) == 1 and content[0]["type"] == "text":
                content = content[0]["text"]

            anthropic_messages.append({
                "role": msg.role,
                "content": content,
            })

        return system_prompt, anthropic_messages

    def _prepare_image(self, image: Union[str, Path, bytes]) -> Dict:
        """
        Prepare image content for Anthropic API.

        Args:
            image: Image path, URL, or bytes

        Returns:
            Image content dict for API
        """
        # Handle URLs
        if isinstance(image, str) and image.startswith(("http://", "https://")):
            return {
                "type": "image",
                "source": {
                    "type": "url",
                    "url": image,
                },
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
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": data,
                },
            }

        # Handle bytes
        if isinstance(image, bytes):
            data = base64.b64encode(image).decode("utf-8")

            # Detect MIME from magic bytes
            if image.startswith(b"\x89PNG"):
                mime_type = "image/png"
            elif image.startswith(b"\xff\xd8\xff"):
                mime_type = "image/jpeg"
            elif image.startswith(b"GIF8"):
                mime_type = "image/gif"
            else:
                mime_type = "image/png"

            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": data,
                },
            }

        raise ValueError(f"Unsupported image type: {type(image)}")
