"""
Async/Sync Adapter Utilities

Provides utilities for bridging async and sync code, particularly useful for:
- Using async LLM providers in sync Flask applications
- Converting AsyncGenerators to sync Generators for SSE streaming
- Thread pool executor patterns for async operations

Extracted from lessonplanner Phase 2 migration pattern.

Example:
    from shared.utils.async_adapter import async_to_sync, async_generator_to_sync

    # Convert async function to sync
    @async_to_sync
    async def fetch_data():
        return await api.get_data()

    # Use in sync context
    result = fetch_data()

    # Convert async generator to sync generator
    async def stream_data():
        for i in range(10):
            yield i

    for chunk in async_generator_to_sync(stream_data()):
        print(chunk)
"""

import asyncio
import concurrent.futures
from typing import TypeVar, Callable, AsyncGenerator, Generator, Any, Optional
from functools import wraps


T = TypeVar('T')


class AsyncAdapter:
    """
    Adapter for running async code in sync contexts.

    Uses a thread pool executor to run async operations without blocking
    the main thread. Useful for Flask applications that need to call async
    LLM providers.

    Usage:
        adapter = AsyncAdapter(max_workers=4)
        result = adapter.run(async_function(arg1, arg2))
        adapter.shutdown()

    Or as context manager:
        with AsyncAdapter() as adapter:
            result = adapter.run(async_function())
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize async adapter.

        Args:
            max_workers: Maximum number of threads (default: None = number of CPUs)
        """
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._loop = None

    def _get_or_create_loop(self):
        """Get or create an event loop for this thread."""
        try:
            # Try to get existing loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Loop is closed")
            return loop
        except RuntimeError:
            # Create new loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def run(self, coro) -> Any:
        """
        Run an async coroutine in a sync context.

        Args:
            coro: Async coroutine to run

        Returns:
            Result of the coroutine
        """
        def run_in_thread():
            loop = self._get_or_create_loop()
            return loop.run_until_complete(coro)

        future = self.executor.submit(run_in_thread)
        return future.result()

    def shutdown(self, wait: bool = True):
        """
        Shutdown the executor.

        Args:
            wait: Whether to wait for pending futures
        """
        self.executor.shutdown(wait=wait)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


def async_to_sync(async_func: Callable) -> Callable:
    """
    Decorator to convert an async function to a sync function.

    Args:
        async_func: Async function to convert

    Returns:
        Sync version of the function

    Example:
        @async_to_sync
        async def fetch_data(url):
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return response.json()

        # Use as sync function
        data = fetch_data('https://api.example.com/data')
    """
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        with AsyncAdapter() as adapter:
            return adapter.run(async_func(*args, **kwargs))

    return wrapper


def async_generator_to_sync(
    async_gen: AsyncGenerator[T, None],
    timeout: Optional[float] = None
) -> Generator[T, None, None]:
    """
    Convert an AsyncGenerator to a sync Generator.

    This is particularly useful for Flask SSE streaming where you need
    to yield from an async generator in a sync view function.

    Args:
        async_gen: Async generator to convert
        timeout: Optional timeout for each iteration

    Yields:
        Items from the async generator

    Example:
        async def async_stream():
            for i in range(10):
                await asyncio.sleep(0.1)
                yield f"Item {i}"

        # Use in Flask SSE endpoint
        def stream_endpoint():
            def generate():
                for chunk in async_generator_to_sync(async_stream()):
                    yield f"data: {chunk}\n\n"
            return Response(generate(), mimetype='text/event-stream')
    """
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        while True:
            try:
                # Get next item from async generator
                if timeout:
                    item = loop.run_until_complete(
                        asyncio.wait_for(async_gen.__anext__(), timeout=timeout)
                    )
                else:
                    item = loop.run_until_complete(async_gen.__anext__())

                yield item

            except StopAsyncIteration:
                break

    finally:
        # Clean up
        try:
            loop.run_until_complete(async_gen.aclose())
        except:
            pass
        loop.close()


def run_async_in_thread(coro) -> Any:
    """
    Run an async coroutine in a separate thread.

    This is a one-off execution utility. For repeated calls, use AsyncAdapter.

    Args:
        coro: Async coroutine to run

    Returns:
        Result of the coroutine

    Example:
        async def fetch_data():
            return await api.get_data()

        result = run_async_in_thread(fetch_data())
    """
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_in_thread)
        return future.result()


class AsyncStreamAdapter:
    """
    Adapter for streaming async generators in sync contexts.

    Manages the event loop and handles cleanup automatically.

    Usage:
        async def stream_data():
            for i in range(10):
                yield i

        with AsyncStreamAdapter(stream_data()) as adapter:
            for chunk in adapter:
                print(chunk)
    """

    def __init__(self, async_gen: AsyncGenerator):
        """
        Initialize stream adapter.

        Args:
            async_gen: Async generator to adapt
        """
        self.async_gen = async_gen
        self.loop = None

    def __enter__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.loop:
            try:
                self.loop.run_until_complete(self.async_gen.aclose())
            except:
                pass
            self.loop.close()

    def __iter__(self):
        return self

    def __next__(self):
        if not self.loop:
            raise RuntimeError("AsyncStreamAdapter not initialized. Use as context manager.")

        try:
            return self.loop.run_until_complete(self.async_gen.__anext__())
        except StopAsyncIteration:
            raise StopIteration


# Global adapter instance for convenience
_global_adapter = None


def get_global_adapter() -> AsyncAdapter:
    """
    Get or create a global AsyncAdapter instance.

    Returns:
        Global AsyncAdapter instance
    """
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = AsyncAdapter()
    return _global_adapter


def shutdown_global_adapter():
    """Shutdown the global AsyncAdapter instance."""
    global _global_adapter
    if _global_adapter is not None:
        _global_adapter.shutdown()
        _global_adapter = None
