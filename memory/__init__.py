"""
Memory and caching utilities.

Provides Redis-based caching and state management:
- Key-value storage
- TTL support
- Semantic caching for LLM responses
- Rate limiting
"""

from typing import Optional, Any
import json
import os


class RedisManager:
    """Redis connection and caching manager."""

    def __init__(self, host: str = None, port: int = None, db: int = 0):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", 6379))
        self.db = db
        self.client = None

        try:
            import redis
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
            # Test connection
            self.client.ping()
        except ImportError:
            raise ImportError("redis package is required. Install with: pip install redis")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis at {self.host}:{self.port}: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis."""
        value = self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set a value in Redis with optional TTL (seconds)."""
        if not isinstance(value, str):
            value = json.dumps(value)

        if ttl:
            return self.client.setex(key, ttl, value)
        return self.client.set(key, value)

    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        return self.client.delete(key) > 0

    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        return self.client.exists(key) > 0

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        return self.client.incrby(key, amount)

    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on an existing key."""
        return self.client.expire(key, ttl)
