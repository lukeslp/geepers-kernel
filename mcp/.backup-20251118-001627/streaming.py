"""
MCP Streaming Infrastructure

Server-Sent Events (SSE) bridge and webhook support for real-time
orchestrator progress updates.

Enables real-time streaming of orchestrator events to web clients and
async notification delivery via webhooks.

Author: Luke Steuber
"""

import asyncio
import json
import logging
import hmac
import hashlib
import time
from typing import Dict, Optional, Callable, Any, AsyncIterator
from datetime import datetime, timedelta
from collections import defaultdict
import aiohttp

logger = logging.getLogger(__name__)


class StreamingBridge:
    """
    Bridge between orchestrator events and SSE/WebSocket clients

    Manages multiple concurrent streams, each identified by a task_id.
    Orchestrators push events to streams, and clients consume them via SSE.
    """

    def __init__(self, max_streams: int = 100, stream_ttl: int = 3600):
        """
        Initialize streaming bridge

        Args:
            max_streams: Maximum number of concurrent streams
            stream_ttl: Stream time-to-live in seconds (cleanup old streams)
        """
        self.max_streams = max_streams
        self.stream_ttl = stream_ttl

        # task_id -> asyncio.Queue
        self.active_streams: Dict[str, asyncio.Queue] = {}

        # task_id -> creation timestamp
        self.stream_timestamps: Dict[str, float] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Start cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    async def create_stream(self, task_id: str) -> asyncio.Queue:
        """
        Create a new stream for a task

        Args:
            task_id: Unique task identifier

        Returns:
            Queue for receiving events

        Raises:
            ValueError: If max_streams exceeded
        """
        async with self._lock:
            # Check limit
            if len(self.active_streams) >= self.max_streams:
                # Try to cleanup old streams first
                await self._cleanup_old_streams()

                if len(self.active_streams) >= self.max_streams:
                    raise ValueError(
                        f"Max streams ({self.max_streams}) exceeded. "
                        f"Close existing streams first."
                    )

            # Create queue
            queue = asyncio.Queue(maxsize=1000)
            self.active_streams[task_id] = queue
            self.stream_timestamps[task_id] = time.time()

            logger.info(f"Created stream for task {task_id}")
            return queue

    async def get_stream(self, task_id: str) -> Optional[asyncio.Queue]:
        """
        Get existing stream for a task

        Args:
            task_id: Task identifier

        Returns:
            Queue if stream exists, None otherwise
        """
        return self.active_streams.get(task_id)

    async def push_event(
        self,
        task_id: str,
        event: Dict[str, Any],
        create_if_missing: bool = False
    ) -> bool:
        """
        Push event to a stream

        Args:
            task_id: Task identifier
            event: Event dict to push
            create_if_missing: Create stream if it doesn't exist

        Returns:
            True if event was pushed, False if stream doesn't exist
        """
        queue = self.active_streams.get(task_id)

        if not queue and create_if_missing:
            queue = await self.create_stream(task_id)

        if not queue:
            logger.warning(f"No stream for task {task_id}")
            return False

        try:
            # Add timestamp if not present
            if 'timestamp' not in event:
                event['timestamp'] = datetime.utcnow().isoformat()

            await queue.put(event)
            return True

        except asyncio.QueueFull:
            logger.error(f"Queue full for task {task_id}")
            return False

    async def close_stream(self, task_id: str):
        """
        Close a stream (send sentinel and cleanup)

        Args:
            task_id: Task identifier
        """
        async with self._lock:
            queue = self.active_streams.get(task_id)

            if queue:
                # Send sentinel to signal end of stream
                await queue.put(None)

                # Remove from tracking
                del self.active_streams[task_id]
                if task_id in self.stream_timestamps:
                    del self.stream_timestamps[task_id]

                logger.info(f"Closed stream for task {task_id}")

    async def consume_stream(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Consume events from a stream (async generator for SSE)

        Args:
            task_id: Task identifier
            timeout: Optional timeout for waiting for events

        Yields:
            Event dicts until stream closes

        Example:
            async for event in bridge.consume_stream(task_id):
                yield f"data: {json.dumps(event)}\\n\\n"
        """
        queue = await self.get_stream(task_id)

        if not queue:
            logger.warning(f"No stream for task {task_id}")
            return

        try:
            while True:
                try:
                    # Wait for event with optional timeout
                    if timeout:
                        event = await asyncio.wait_for(
                            queue.get(),
                            timeout=timeout
                        )
                    else:
                        event = await queue.get()

                    # None is sentinel for end of stream
                    if event is None:
                        break

                    yield event

                except asyncio.TimeoutError:
                    # Send keepalive on timeout
                    yield {"event_type": "keepalive", "timestamp": datetime.utcnow().isoformat()}

        except Exception as e:
            logger.error(f"Error consuming stream {task_id}: {e}")

        finally:
            # Auto-close stream after consumption
            await self.close_stream(task_id)

    async def _cleanup_old_streams(self):
        """Cleanup streams older than TTL"""
        now = time.time()
        to_remove = []

        for task_id, timestamp in self.stream_timestamps.items():
            if (now - timestamp) > self.stream_ttl:
                to_remove.append(task_id)

        for task_id in to_remove:
            await self.close_stream(task_id)
            logger.info(f"Cleaned up old stream: {task_id}")

    async def start_cleanup_loop(self, interval: int = 300):
        """
        Start background cleanup loop

        Args:
            interval: Cleanup interval in seconds
        """
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval)
                await self._cleanup_old_streams()

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def stop_cleanup_loop(self):
        """Stop background cleanup loop"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        return {
            "active_streams": len(self.active_streams),
            "max_streams": self.max_streams,
            "stream_ttl": self.stream_ttl,
            "task_ids": list(self.active_streams.keys())
        }


class WebhookManager:
    """
    Manages webhook deliveries for async notifications

    Delivers events to registered webhook URLs with retry logic,
    signature verification, and delivery tracking.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize webhook manager

        Args:
            secret_key: Secret key for HMAC signatures (optional)
            max_retries: Maximum delivery retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.secret_key = secret_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # task_id -> webhook_url
        self.registered_webhooks: Dict[str, str] = {}

        # Delivery stats
        self.delivery_count = defaultdict(int)  # task_id -> count
        self.failure_count = defaultdict(int)   # task_id -> count

    def register_webhook(self, task_id: str, webhook_url: str):
        """
        Register webhook for a task

        Args:
            task_id: Task identifier
            webhook_url: Webhook URL to deliver to
        """
        self.registered_webhooks[task_id] = webhook_url
        logger.info(f"Registered webhook for task {task_id}: {webhook_url}")

    def unregister_webhook(self, task_id: str):
        """
        Unregister webhook for a task

        Args:
            task_id: Task identifier
        """
        if task_id in self.registered_webhooks:
            del self.registered_webhooks[task_id]
            logger.info(f"Unregistered webhook for task {task_id}")

    def get_webhook(self, task_id: str) -> Optional[str]:
        """
        Get webhook URL for a task

        Args:
            task_id: Task identifier

        Returns:
            Webhook URL if registered, None otherwise
        """
        return self.registered_webhooks.get(task_id)

    async def deliver_event(
        self,
        task_id: str,
        event: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> bool:
        """
        Deliver event to webhook

        Args:
            task_id: Task identifier
            event: Event dict to deliver
            webhook_url: Optional webhook URL (uses registered if not provided)

        Returns:
            True if delivered successfully, False otherwise
        """
        url = webhook_url or self.registered_webhooks.get(task_id)

        if not url:
            logger.warning(f"No webhook registered for task {task_id}")
            return False

        # Prepare payload
        payload = {
            "task_id": task_id,
            "event": event,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add signature if secret key is set
        headers = {"Content-Type": "application/json"}

        if self.secret_key:
            signature = self._generate_signature(payload)
            headers["X-Webhook-Signature"] = signature

        # Retry loop with exponential backoff
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status < 400:
                            self.delivery_count[task_id] += 1
                            logger.info(
                                f"Webhook delivered for task {task_id} "
                                f"(status: {response.status})"
                            )
                            return True
                        else:
                            logger.warning(
                                f"Webhook delivery failed (status: {response.status})"
                            )

            except Exception as e:
                logger.error(f"Webhook delivery error: {e}")

            # Retry with exponential backoff
            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** attempt)
                logger.info(f"Retrying webhook delivery in {delay}s...")
                await asyncio.sleep(delay)

        # All retries failed
        self.failure_count[task_id] += 1
        logger.error(f"Webhook delivery failed after {self.max_retries} retries")
        return False

    def _generate_signature(self, payload: Dict[str, Any]) -> str:
        """
        Generate HMAC signature for payload

        Args:
            payload: Payload dict

        Returns:
            HMAC signature (hex)
        """
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return signature

    @staticmethod
    def verify_signature(
        payload: Dict[str, Any],
        signature: str,
        secret_key: str
    ) -> bool:
        """
        Verify HMAC signature

        Args:
            payload: Payload dict
            signature: Signature to verify
            secret_key: Secret key

        Returns:
            True if signature is valid, False otherwise
        """
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def get_stats(self) -> Dict[str, Any]:
        """Get webhook statistics"""
        return {
            "registered_webhooks": len(self.registered_webhooks),
            "total_deliveries": sum(self.delivery_count.values()),
            "total_failures": sum(self.failure_count.values()),
            "delivery_count_by_task": dict(self.delivery_count),
            "failure_count_by_task": dict(self.failure_count)
        }


# Singleton instances
_streaming_bridge: Optional[StreamingBridge] = None
_webhook_manager: Optional[WebhookManager] = None


def get_streaming_bridge() -> StreamingBridge:
    """Get global StreamingBridge instance"""
    global _streaming_bridge
    if _streaming_bridge is None:
        _streaming_bridge = StreamingBridge()
    return _streaming_bridge


def get_webhook_manager() -> WebhookManager:
    """Get global WebhookManager instance"""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager
