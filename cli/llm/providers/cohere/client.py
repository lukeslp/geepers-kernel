"""
Cohere Provider Implementation.

Client for Cohere Command and Embed models.

Author: Luke Steuber
"""

import os
from typing import Optional, List, Dict, Any, Iterator, Union

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False

from ..base import (
    BaseProvider,
    Capabilities,
    Message,
    CompletionResponse,
    EmbeddingResponse,
)


class CohereProvider(BaseProvider):
    """
    Cohere API Provider.

    Supports:
    - Text generation (Command R+, Command R)
    - Embeddings (Embed v3)
    """

    name = "cohere"
    env_key = "COHERE_API_KEY"
    default_model = "command-r-08-2024"

    capabilities = Capabilities(
        text=True,
        vision=False,
        audio=False,
        video=False,
        image_gen=False,
        tts=False,
        embedding=True,
    )

    # Model constants
    DEFAULT_CHAT_MODEL = "command-r-08-2024"
    DEFAULT_EMBED_MODEL = "embed-english-v3.0"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Cohere provider.

        Args:
            api_key: Cohere API key (falls back to COHERE_API_KEY env var)
            model: Default model to use
        """
        if not COHERE_AVAILABLE:
            raise ImportError(
                "cohere package not installed. "
                "Install with: pip install cohere"
            )

        self.api_key = api_key or os.getenv(self.env_key)
        if not self.api_key:
            raise ValueError(f"No API key found. Set {self.env_key} environment variable.")

        self.model = model or self.default_model
        self.client = cohere.ClientV2(api_key=self.api_key)

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
        Generate a chat completion with Cohere.

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

        cohere_messages = self._build_messages(messages)

        response = self.client.chat(
            model=use_model,
            messages=cohere_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = ""
        if response.message and response.message.content:
            for part in response.message.content:
                if hasattr(part, "text"):
                    content += part.text

        return CompletionResponse(
            content=content,
            model=use_model,
            usage={
                "prompt_tokens": response.usage.tokens.input_tokens if response.usage else 0,
                "completion_tokens": response.usage.tokens.output_tokens if response.usage else 0,
            } if response.usage else None,
            finish_reason=response.finish_reason,
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
        Stream a chat completion with Cohere.

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

        cohere_messages = self._build_messages(messages)

        stream = self.client.chat_stream(
            model=use_model,
            messages=cohere_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        for event in stream:
            if event.type == "content-delta" and hasattr(event, "delta"):
                if hasattr(event.delta, "message") and event.delta.message:
                    if hasattr(event.delta.message, "content") and event.delta.message.content:
                        for part in event.delta.message.content:
                            if hasattr(part, "text"):
                                yield part.text

    # =========================================================================
    # Embeddings
    # =========================================================================

    def embed(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
        input_type: str = "search_document",
        **kwargs,
    ) -> Union[EmbeddingResponse, List[EmbeddingResponse]]:
        """
        Generate embeddings with Cohere.

        Args:
            text: Text or list of texts to embed
            model: Embedding model
            input_type: Type of input (search_document, search_query, classification, clustering)

        Returns:
            EmbeddingResponse or list of EmbeddingResponse
        """
        use_model = model or self.DEFAULT_EMBED_MODEL

        if isinstance(text, str):
            texts = [text]
        else:
            texts = text

        response = self.client.embed(
            model=use_model,
            texts=texts,
            input_type=input_type,
            embedding_types=["float"],
        )

        embeddings = response.embeddings.float_

        if isinstance(text, str):
            return EmbeddingResponse(
                embedding=embeddings[0],
                model=use_model,
            )
        else:
            return [
                EmbeddingResponse(embedding=emb, model=use_model)
                for emb in embeddings
            ]

    # =========================================================================
    # Model Listing
    # =========================================================================

    def list_models(self) -> List[Dict[str, Any]]:
        """List available Cohere models."""
        return [
            {"name": "command-r-plus", "description": "Most capable", "context": 128000},
            {"name": "command-r", "description": "Balanced", "context": 128000},
            {"name": "command-light", "description": "Fast", "context": 4096},
            {"name": "embed-english-v3.0", "description": "English embeddings", "dimensions": 1024},
            {"name": "embed-multilingual-v3.0", "description": "Multilingual embeddings", "dimensions": 1024},
        ]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_messages(self, messages: List[Message]) -> List[Dict]:
        """Convert Message objects to Cohere format."""
        cohere_messages = []

        for msg in messages:
            role = msg.role
            if role == "system":
                role = "system"
            elif role == "assistant":
                role = "assistant"
            else:
                role = "user"

            cohere_messages.append({
                "role": role,
                "content": msg.content,
            })

        return cohere_messages
