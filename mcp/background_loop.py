"""
Background Event Loop Manager

Provides a persistent asyncio event loop running in a daemon thread
for long-running background tasks in Flask applications.

This solves the issue where @async_to_sync creates temporary event loops
that destroy background tasks when requests complete.

Author: Luke Steuber
"""

import asyncio
import threading
import logging
from typing import Coroutine, Any

logger = logging.getLogger(__name__)


class BackgroundEventLoop:
    """
    Manages a persistent asyncio event loop in a background thread.

    This allows Flask applications to submit long-running async tasks
    that survive beyond the HTTP request lifecycle.
    """

    def __init__(self):
        """Initialize background event loop."""
        self._loop = None
        self._thread = None
        self._started = threading.Event()

    def start(self):
        """Start the background event loop in a daemon thread."""
        if self._thread is not None:
            logger.warning("Background event loop already started")
            return

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Wait for loop to be ready
        self._started.wait(timeout=5.0)
        logger.info("Background event loop started")

    def _run_loop(self):
        """Run the event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._started.set()

        try:
            logger.info("Event loop running in background thread")
            self._loop.run_forever()
        finally:
            logger.info("Event loop stopping")
            self._loop.close()

    def submit_task(self, coro: Coroutine) -> asyncio.Task:
        """
        Submit a coroutine to run in the background loop.

        Args:
            coro: Coroutine to execute

        Returns:
            asyncio.Task object
        """
        if self._loop is None:
            raise RuntimeError("Background loop not started")

        # Schedule the coroutine in the background loop
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        # Wrap in a task-like object that we can track
        return future

    def run_sync(self, coro: Coroutine, timeout: float = None) -> Any:
        """
        Run a coroutine synchronously and wait for result.

        Args:
            coro: Coroutine to execute
            timeout: Optional timeout in seconds

        Returns:
            Result of the coroutine
        """
        if self._loop is None:
            raise RuntimeError("Background loop not started")

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def stop(self):
        """Stop the background event loop."""
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=5.0)
            self._loop = None
            self._thread = None
            logger.info("Background event loop stopped")


# Global background loop instance
_background_loop = None


def get_background_loop() -> BackgroundEventLoop:
    """
    Get or create the global background event loop.

    Returns:
        BackgroundEventLoop instance
    """
    global _background_loop
    if _background_loop is None:
        _background_loop = BackgroundEventLoop()
        _background_loop.start()
    return _background_loop


def submit_background_task(coro: Coroutine) -> asyncio.Task:
    """
    Submit a coroutine to the background loop.

    Args:
        coro: Coroutine to execute

    Returns:
        Task handle
    """
    loop = get_background_loop()
    return loop.submit_task(coro)


def run_async_sync(coro: Coroutine, timeout: float = None) -> Any:
    """
    Run an async coroutine synchronously using the background loop.

    Args:
        coro: Coroutine to execute
        timeout: Optional timeout in seconds

    Returns:
        Result of the coroutine
    """
    loop = get_background_loop()
    return loop.run_sync(coro, timeout=timeout)
