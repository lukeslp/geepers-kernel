"""
Perplexity Provider Implementation.

Client for Perplexity Sonar models with web-grounded responses.

Author: Luke Steuber
"""

import os
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
)


class PerplexityProvider(BaseProvider):
    """
    Perplexity API Provider.

    Uses OpenAI-compatible API with Perplexity base URL.
    Returns web-grounded responses with citations.

    Supports:
    - Text generation with citations (Sonar, Sonar Pro)
    """

    name = "perplexity"
    env_key = "PERPLEXITY_API_KEY"
    default_model = "sonar-pro"

    capabilities = Capabilities(
        text=True,
        vision=False,
        audio=False,
        video=False,
        image_gen=False,
        tts=False,
        embedding=False,
    )

    # API endpoint
    BASE_URL = "https://api.perplexity.ai"

    # Model constants
    DEFAULT_CHAT_MODEL = "sonar-pro"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Perplexity provider.

        Args:
            api_key: Perplexity API key (falls back to PERPLEXITY_API_KEY env var)
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

        # Perplexity uses OpenAI-compatible API
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
        Generate a chat completion with Perplexity.

        Responses include web-grounded information with citations.

        Args:
            messages: Prompt string or list of Message objects
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            CompletionResponse with generated text and citations
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

        # Extract citations if available
        citations = None
        if hasattr(response, "citations"):
            citations = response.citations

        return CompletionResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            finish_reason=response.choices[0].finish_reason,
            metadata={"citations": citations} if citations else None,
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
        Stream a chat completion with Perplexity.

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
    # Model Listing
    # =========================================================================

    def list_models(self) -> List[Dict[str, Any]]:
        """List available Perplexity models."""
        return [
            {
                "name": "sonar-pro",
                "description": "Advanced with citations",
                "context": 200000,
            },
            {
                "name": "sonar",
                "description": "Standard with citations",
                "context": 128000,
            },
            {
                "name": "sonar-reasoning-pro",
                "description": "Advanced reasoning",
                "context": 128000,
            },
            {
                "name": "sonar-reasoning",
                "description": "Standard reasoning",
                "context": 128000,
            },
        ]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_messages(self, messages: List[Message]) -> List[Dict]:
        """Convert Message objects to OpenAI format."""
        openai_messages = []

        for msg in messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        return openai_messages
