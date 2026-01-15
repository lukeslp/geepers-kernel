"""
Retry helpers for synchronous and asynchronous callables.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterable, Optional, Tuple, Type, TypeVar

import logging

__all__ = ["RetryConfig", "retry", "async_retry"]

T = TypeVar("T")

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration shared by retry helpers."""

    max_attempts: int = 3
    delay: float = 1.0
    backoff: float = 2.0
    jitter: float = 0.2
    retry_exceptions: Tuple[Type[BaseException], ...] = (Exception,)

    def compute_delay(self, attempt: int) -> float:
        base = self.delay * (self.backoff ** attempt)
        if self.jitter:
            jitter_amount = base * self.jitter
            return max(0.0, base + random.uniform(-jitter_amount, jitter_amount))
        return base


def retry(
    *,
    config: Optional[RetryConfig] = None,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.2,
    exceptions: Optional[Iterable[Type[BaseException]]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator for synchronous functions.

    Args mirror `RetryConfig`. Either pass a config instance or override fields.
    """

    retry_config = config or RetryConfig(
        max_attempts=max_attempts,
        delay=delay,
        backoff=backoff,
        jitter=jitter,
        retry_exceptions=tuple(exceptions) if exceptions else (Exception,),
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[BaseException] = None
            for attempt in range(retry_config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_config.retry_exceptions as exc:  # type: ignore[attr-defined]
                    last_exception = exc
                    if attempt >= retry_config.max_attempts - 1:
                        logger.error(
                            "Function %s failed after %s attempts",
                            func.__name__,
                            retry_config.max_attempts,
                            exc_info=True,
                        )
                        break

                    sleep_time = retry_config.compute_delay(attempt)
                    logger.warning(
                        "Function %s failed (attempt %s/%s). Retrying in %.2fs: %s",
                        func.__name__,
                        attempt + 1,
                        retry_config.max_attempts,
                        sleep_time,
                        exc,
                    )
                    time.sleep(sleep_time)
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry wrapper terminated without executing function.")

        return wrapper

    return decorator


def async_retry(
    *,
    config: Optional[RetryConfig] = None,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.2,
    exceptions: Optional[Iterable[Type[BaseException]]] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Retry decorator for asynchronous callables.
    """

    retry_config = config or RetryConfig(
        max_attempts=max_attempts,
        delay=delay,
        backoff=backoff,
        jitter=jitter,
        retry_exceptions=tuple(exceptions) if exceptions else (Exception,),
    )

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[BaseException] = None
            for attempt in range(retry_config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retry_config.retry_exceptions as exc:  # type: ignore[attr-defined]
                    last_exception = exc
                    if attempt >= retry_config.max_attempts - 1:
                        logger.error(
                            "Coroutine %s failed after %s attempts",
                            func.__name__,
                            retry_config.max_attempts,
                            exc_info=True,
                        )
                        break

                    sleep_time = retry_config.compute_delay(attempt)
                    logger.warning(
                        "Coroutine %s failed (attempt %s/%s). Retrying in %.2fs: %s",
                        func.__name__,
                        attempt + 1,
                        retry_config.max_attempts,
                        sleep_time,
                        exc,
                    )
                    await asyncio.sleep(sleep_time)
            if last_exception:
                raise last_exception
            raise RuntimeError("Async retry wrapper terminated without executing coroutine.")

        return wrapper

    return decorator

