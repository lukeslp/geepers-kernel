"""
Rate limiting utilities for Flask applications.

Provides simple in-memory and Redis-backed rate limiting.
"""

import time
from typing import Optional
from functools import wraps
from flask import jsonify


class RateLimiter:
    """
    Simple rate limiter with sliding window.

    Supports in-memory (development) or Redis-backed (production).
    """

    def __init__(self, requests_per_minute: int = 20, use_redis: bool = False, redis_client=None):
        self.requests_per_minute = requests_per_minute
        self.use_redis = use_redis
        self.redis_client = redis_client

        # In-memory storage (fallback)
        self.request_history = []

    def check_limit(self, key: Optional[str] = None) -> bool:
        """
        Check if request is within rate limit.

        Args:
            key: Optional key for per-user rate limiting (IP, user ID, etc.)
                 If None, uses global rate limiting.

        Returns:
            True if request allowed, False if rate limited
        """
        if self.use_redis and self.redis_client:
            return self._check_redis(key or 'global')
        else:
            return self._check_memory()

    def _check_memory(self) -> bool:
        """In-memory rate limit check"""
        current_time = time.time()

        # Remove requests older than 1 minute
        self.request_history = [
            req_time for req_time in self.request_history
            if current_time - req_time < 60
        ]

        if len(self.request_history) >= self.requests_per_minute:
            return False

        self.request_history.append(current_time)
        return True

    def _check_redis(self, key: str) -> bool:
        """Redis-backed rate limit check (sliding window)"""
        if not self.redis_client:
            return self._check_memory()

        current_time = int(time.time())
        window_key = f"rate_limit:{key}:{current_time // 60}"

        try:
            # Increment counter
            count = self.redis_client.incr(window_key)

            # Set expiry on first request
            if count == 1:
                self.redis_client.expire(window_key, 120)  # 2 minutes TTL

            return count <= self.requests_per_minute

        except Exception:
            # Fallback to memory if Redis fails
            return self._check_memory()

    def limit(self, func=None, key_func=None):
        """
        Decorator to rate limit a Flask route.

        Args:
            func: Function to decorate (if using without arguments)
            key_func: Optional function to extract rate limit key from request
                      e.g., lambda: request.remote_addr for per-IP limiting

        Example:
            @app.route('/api/chat')
            @rate_limiter.limit()
            def chat():
                return "Hello"

            # Per-IP limiting
            @app.route('/api/chat')
            @rate_limiter.limit(key_func=lambda: request.remote_addr)
            def chat():
                return "Hello"
        """
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                key = key_func() if key_func else None

                if not self.check_limit(key):
                    return jsonify({
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {self.requests_per_minute} requests per minute"
                    }), 429

                return f(*args, **kwargs)

            return wrapped

        # Handle both @limiter.limit() and @limiter.limit
        if func is None:
            return decorator
        else:
            return decorator(func)
