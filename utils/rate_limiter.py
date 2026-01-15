"""
In-memory rate limiting helpers.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, TypeVar

__all__ = ["TokenBucket", "InMemoryRateLimiter", "rate_limit"]

T = TypeVar("T")


@dataclass
class TokenBucket:
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default=0)
    updated_at: float = field(default_factory=time.time)

    def consume(self, tokens: float = 1) -> bool:
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.updated_at
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.updated_at = now


class InMemoryRateLimiter:
    """
    Thread-safe in-memory rate limiter using token buckets.

    Suitable for small deployments or unit tests. For production,
    prefer Redis-backed implementations (see shared.memory.redis_manager).
    """

    def __init__(self) -> None:
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def register_bucket(self, key: str, capacity: int, refill_rate: float) -> None:
        with self._lock:
            self._buckets[key] = TokenBucket(
                capacity=capacity,
                refill_rate=refill_rate,
                tokens=float(capacity),
            )

    def check(self, key: str, tokens: float = 1.0) -> bool:
        with self._lock:
            bucket = self._buckets.get(key)
            if not bucket:
                raise KeyError(f"No bucket registered for key '{key}'")
            return bucket.consume(tokens)


def rate_limit(
    limiter: InMemoryRateLimiter,
    key: str,
    *,
    capacity: int,
    refill_rate: float,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that rate limits function calls using a shared limiter instance.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        limiter.register_bucket(key, capacity, refill_rate)

        def wrapper(*args, **kwargs):
            if not limiter.check(key):
                raise RuntimeError(f"Rate limit exceeded for key '{key}'")
            return func(*args, **kwargs)

        return wrapper

    return decorator

