"""
Anthropic (Claude) provider implementation.
Supports Claude chat models, vision capabilities, and batch processing.
"""

from typing import List, Union, Optional, Dict, Any
from dataclasses import dataclass
from . import BaseLLMProvider, Message, CompletionResponse
import os
import base64


@dataclass
class BatchRequest:
    """A single request in a batch."""
    custom_id: str
    messages: List[Message]
    model: Optional[str] = None
    max_tokens: int = 1024
    system: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BatchResponse:
    """Response from batch operations."""
    batch_id: str
    status: str  # 'in_progress', 'ended', 'canceling', 'canceled'
    created_at: str
    ended_at: Optional[str] = None
    request_counts: Optional[Dict[str, int]] = None
    results: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str = None, model: str = None):
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        model = model or self.DEFAULT_MODEL
        super().__init__(api_key, model)

        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")

    def complete(self, messages: List[Message], **kwargs) -> CompletionResponse:
        """Generate a completion using Claude."""
        # Anthropic requires system messages as a top-level parameter, not in messages
        system_parts = []
        formatted_messages = []
        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                formatted_messages.append({"role": msg.role, "content": msg.content})

        # Parameters forwarded to Anthropic API
        _passthrough_skip = {"model", "max_tokens", "system", "effort", "thinking",
                             "inference_geo", "extended_thinking", "budget_tokens"}
        create_kwargs = {
            "model": kwargs.get("model", self.model),
            "messages": formatted_messages,
            "max_tokens": kwargs.get("max_tokens", 1024),
            **{k: v for k, v in kwargs.items() if k not in _passthrough_skip}
        }

        if system_parts:
            create_kwargs["system"] = "\n\n".join(system_parts)
        elif "system" in kwargs:
            create_kwargs["system"] = kwargs["system"]

        # Extended thinking — Claude 4.x
        # Opus 4.6 uses adaptive thinking; Sonnet 4.x / Opus 4.5 use enabled + budget_tokens
        if "thinking" in kwargs:
            create_kwargs["thinking"] = kwargs["thinking"]
        elif kwargs.get("extended_thinking"):
            model_name = create_kwargs["model"]
            if "opus-4-6" in model_name:
                create_kwargs["thinking"] = {"type": "adaptive"}
            else:
                budget = kwargs.get("budget_tokens", 5000)
                create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

        # effort parameter — GA as of Feb 5, 2026; controls thinking depth on Opus 4.6
        if "effort" in kwargs:
            create_kwargs["effort"] = kwargs["effort"]

        # Data residency — specify inference geography (inference_geo)
        if "inference_geo" in kwargs:
            create_kwargs["inference_geo"] = kwargs["inference_geo"]

        response = self.client.messages.create(**create_kwargs)

        # Extract text from first text block (backwards compat)
        text_parts = [b.text for b in response.content if hasattr(b, "text")]
        content_text = text_parts[0] if text_parts else ""

        # When tool_use is present, serialize all content blocks for passthrough
        raw_blocks = None
        if response.stop_reason == "tool_use":
            raw_blocks = []
            for b in response.content:
                if b.type == "text":
                    raw_blocks.append({"type": "text", "text": b.text})
                elif b.type == "tool_use":
                    raw_blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})

        return CompletionResponse(
            content=content_text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            metadata={"id": response.id, "stop_reason": response.stop_reason},
            content_blocks=raw_blocks,
            stop_reason=response.stop_reason,
        )

    def stream_complete(self, messages: List[Message], **kwargs):
        """Stream a completion using Claude."""
        # Anthropic requires system messages as a top-level parameter, not in messages
        system_parts = []
        formatted_messages = []
        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                formatted_messages.append({"role": msg.role, "content": msg.content})

        stream_kwargs = {
            "model": kwargs.get("model", self.model),
            "messages": formatted_messages,
            "max_tokens": kwargs.get("max_tokens", 1024),
        }
        if system_parts:
            stream_kwargs["system"] = "\n\n".join(system_parts)
        elif "system" in kwargs:
            stream_kwargs["system"] = kwargs["system"]

        # Extended thinking / effort / inference_geo for streaming
        if "thinking" in kwargs:
            stream_kwargs["thinking"] = kwargs["thinking"]
        elif kwargs.get("extended_thinking"):
            model_name = stream_kwargs["model"]
            if "opus-4-6" in model_name:
                stream_kwargs["thinking"] = {"type": "adaptive"}
            else:
                budget = kwargs.get("budget_tokens", 5000)
                stream_kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
        if "effort" in kwargs:
            stream_kwargs["effort"] = kwargs["effort"]
        if "inference_geo" in kwargs:
            stream_kwargs["inference_geo"] = kwargs["inference_geo"]

        with self.client.messages.stream(**stream_kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def list_models(self) -> List[str]:
        """List available Claude models (as of Feb 2026).

        Retired and no longer available:
        - claude-3-7-sonnet (retired Feb 19, 2026)
        - claude-3-5-haiku-20241022 (retired Feb 19, 2026)
        - claude-3-opus-20240229 (retired Jan 5, 2026)
        - claude-3-5-sonnet-20240620/20241022 (retired Oct 28, 2025)
        - claude-2.x, claude-3-sonnet-20240229 (retired Jul 21, 2025)
        """
        return [
            # Claude 4.6 — current generation
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            # Claude 4.5 — previous generation, still available
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
            # Claude 4.1 — available
            "claude-opus-4-1-20250805",
            # Claude 4.0 — available
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            # Claude 3 Haiku — deprecated, retires Apr 19, 2026
            "claude-3-haiku-20240307",
        ]

    def analyze_image(self, image: Union[str, bytes], prompt: str = "Describe this image", **kwargs) -> CompletionResponse:
        """
        Analyze an image using Claude's vision capabilities.

        Args:
            image: Base64-encoded string or raw bytes
            prompt: Question about the image
            **kwargs: Optional parameters
                - model: Claude model (default: "claude-sonnet-4-5-20250929")
                - max_tokens: Maximum response length
                - media_type: Image media type (auto-detected if not provided)

        Returns:
            CompletionResponse with image analysis
        """
        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", 1024)

        # Convert bytes to base64 if needed
        if isinstance(image, bytes):
            image_b64 = base64.b64encode(image).decode('utf-8')
            # Auto-detect media type from bytes
            if image[:8] == b'\x89PNG\r\n\x1a\n':
                media_type = "image/png"
            elif image[:2] == b'\xff\xd8':
                media_type = "image/jpeg"
            elif image[:6] in (b'GIF87a', b'GIF89a'):
                media_type = "image/gif"
            elif image[:4] == b'RIFF' and image[8:12] == b'WEBP':
                media_type = "image/webp"
            else:
                media_type = "image/jpeg"  # Default fallback
        else:
            image_b64 = image
            media_type = "image/jpeg"  # Default for base64 strings

        # Allow override via kwargs
        media_type = kwargs.get("media_type", media_type)

        # Anthropic uses content blocks format
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]

        response = self.client.messages.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens
        )

        return CompletionResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            metadata={
                "id": response.id,
                "stop_reason": response.stop_reason,
                "vision": True
            }
        )

    async def chat(self, messages=None, system_prompt=None, user_prompt=None, **kwargs) -> CompletionResponse:
        """
        Async alias for complete() to support orchestrator compatibility.
        Orchestrators call await chat(system_prompt=..., user_prompt=...)
        but providers use complete(messages=[...]).
        """
        # Convert orchestrator's system_prompt/user_prompt to messages list
        if messages is None and (system_prompt or user_prompt):
            messages = []
            if system_prompt:
                messages.append(Message(role="system", content=system_prompt))
            if user_prompt:
                messages.append(Message(role="user", content=user_prompt))

        # Run sync complete() in thread pool to make it awaitable
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self.complete, messages, **kwargs
        )

    # =========================================================================
    # BATCH PROCESSING (50% cost reduction for async bulk processing)
    # =========================================================================

    def batch_create(self, requests: List[BatchRequest], **kwargs) -> BatchResponse:
        """
        Create a batch of message requests for async processing.

        Batch API offers 50% cost reduction compared to standard API calls.
        Batches complete within 24 hours (typically much faster).

        Args:
            requests: List of BatchRequest objects, each with:
                - custom_id: Unique identifier for tracking (required)
                - messages: List of Message objects
                - model: Model to use (defaults to provider's model)
                - max_tokens: Max tokens for response (default: 1024)
                - system: Optional system prompt
                - metadata: Optional metadata dict
            **kwargs: Additional parameters passed to API

        Returns:
            BatchResponse with batch_id and status

        Example:
            requests = [
                BatchRequest(
                    custom_id="req-1",
                    messages=[Message(role="user", content="Summarize this...")],
                    max_tokens=500
                ),
                BatchRequest(
                    custom_id="req-2",
                    messages=[Message(role="user", content="Translate to French...")],
                    max_tokens=500
                ),
            ]
            batch = provider.batch_create(requests)
            # batch.batch_id can be used to check status later
        """
        # Format requests for Anthropic's batch API
        formatted_requests = []
        for req in requests:
            formatted_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in req.messages
            ]

            params = {
                "model": req.model or self.model,
                "max_tokens": req.max_tokens,
                "messages": formatted_messages,
            }

            if req.system:
                params["system"] = req.system

            formatted_requests.append({
                "custom_id": req.custom_id,
                "params": params
            })

        # Create batch
        response = self.client.messages.batches.create(
            requests=formatted_requests,
            **kwargs
        )

        return BatchResponse(
            batch_id=response.id,
            status=response.processing_status,
            created_at=response.created_at.isoformat() if hasattr(response.created_at, 'isoformat') else str(response.created_at),
            request_counts={
                "processing": response.request_counts.processing,
                "succeeded": response.request_counts.succeeded,
                "errored": response.request_counts.errored,
                "canceled": response.request_counts.canceled,
                "expired": response.request_counts.expired,
            } if response.request_counts else None,
            metadata={"total_requests": len(requests)}
        )

    def batch_status(self, batch_id: str) -> BatchResponse:
        """
        Check the status of a batch.

        Args:
            batch_id: The batch ID returned from batch_create()

        Returns:
            BatchResponse with current status and request counts

        Example:
            status = provider.batch_status(batch.batch_id)
            if status.status == "ended":
                results = provider.batch_results(batch.batch_id)
        """
        response = self.client.messages.batches.retrieve(batch_id)

        return BatchResponse(
            batch_id=response.id,
            status=response.processing_status,
            created_at=response.created_at.isoformat() if hasattr(response.created_at, 'isoformat') else str(response.created_at),
            ended_at=response.ended_at.isoformat() if response.ended_at and hasattr(response.ended_at, 'isoformat') else str(response.ended_at) if response.ended_at else None,
            request_counts={
                "processing": response.request_counts.processing,
                "succeeded": response.request_counts.succeeded,
                "errored": response.request_counts.errored,
                "canceled": response.request_counts.canceled,
                "expired": response.request_counts.expired,
            } if response.request_counts else None
        )

    def batch_results(self, batch_id: str) -> BatchResponse:
        """
        Retrieve results from a completed batch.

        Only call this after batch_status() shows status == "ended".

        Args:
            batch_id: The batch ID to retrieve results for

        Returns:
            BatchResponse with results list containing:
                - custom_id: The ID you provided
                - result: CompletionResponse-like dict with content, model, usage
                - error: Error details if request failed

        Example:
            results = provider.batch_results(batch.batch_id)
            for result in results.results:
                print(f"{result['custom_id']}: {result['result']['content'][:100]}...")
        """
        # Get batch status first
        status_response = self.batch_status(batch_id)

        if status_response.status != "ended":
            return BatchResponse(
                batch_id=batch_id,
                status=status_response.status,
                created_at=status_response.created_at,
                metadata={"error": f"Batch not complete. Status: {status_response.status}"}
            )

        # Stream results from the batch
        results = []
        for result in self.client.messages.batches.results(batch_id):
            if result.result.type == "succeeded":
                message = result.result.message
                results.append({
                    "custom_id": result.custom_id,
                    "result": {
                        "content": message.content[0].text if message.content else "",
                        "model": message.model,
                        "usage": {
                            "prompt_tokens": message.usage.input_tokens,
                            "completion_tokens": message.usage.output_tokens,
                            "total_tokens": message.usage.input_tokens + message.usage.output_tokens,
                        },
                        "stop_reason": message.stop_reason,
                    }
                })
            else:
                results.append({
                    "custom_id": result.custom_id,
                    "error": {
                        "type": result.result.type,
                        "error": str(result.result.error) if hasattr(result.result, 'error') else "Unknown error"
                    }
                })

        return BatchResponse(
            batch_id=batch_id,
            status="ended",
            created_at=status_response.created_at,
            ended_at=status_response.ended_at,
            request_counts=status_response.request_counts,
            results=results,
            metadata={"results_count": len(results)}
        )

    def batch_cancel(self, batch_id: str) -> BatchResponse:
        """
        Cancel a running batch.

        Args:
            batch_id: The batch ID to cancel

        Returns:
            BatchResponse with updated status

        Note:
            Cancellation is not immediate. The batch will transition through
            'canceling' status before reaching 'canceled'.
        """
        response = self.client.messages.batches.cancel(batch_id)

        return BatchResponse(
            batch_id=response.id,
            status=response.processing_status,
            created_at=response.created_at.isoformat() if hasattr(response.created_at, 'isoformat') else str(response.created_at),
            request_counts={
                "processing": response.request_counts.processing,
                "succeeded": response.request_counts.succeeded,
                "errored": response.request_counts.errored,
                "canceled": response.request_counts.canceled,
                "expired": response.request_counts.expired,
            } if response.request_counts else None
        )

    def batch_list(self, limit: int = 20, before_id: str = None, after_id: str = None) -> List[BatchResponse]:
        """
        List all batches for this account.

        Args:
            limit: Maximum number of batches to return (default: 20, max: 100)
            before_id: Return batches created before this batch ID
            after_id: Return batches created after this batch ID

        Returns:
            List of BatchResponse objects
        """
        params = {"limit": min(limit, 100)}
        if before_id:
            params["before_id"] = before_id
        if after_id:
            params["after_id"] = after_id

        response = self.client.messages.batches.list(**params)

        batches = []
        for batch in response.data:
            batches.append(BatchResponse(
                batch_id=batch.id,
                status=batch.processing_status,
                created_at=batch.created_at.isoformat() if hasattr(batch.created_at, 'isoformat') else str(batch.created_at),
                ended_at=batch.ended_at.isoformat() if batch.ended_at and hasattr(batch.ended_at, 'isoformat') else str(batch.ended_at) if batch.ended_at else None,
                request_counts={
                    "processing": batch.request_counts.processing,
                    "succeeded": batch.request_counts.succeeded,
                    "errored": batch.request_counts.errored,
                    "canceled": batch.request_counts.canceled,
                    "expired": batch.request_counts.expired,
                } if batch.request_counts else None
            ))

        return batches
