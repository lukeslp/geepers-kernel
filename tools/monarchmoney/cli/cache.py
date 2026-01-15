"""Simple file-based caching for API responses."""
import json
import time
from pathlib import Path
from typing import Any, Optional
from monarchmoney.logger import logger

CACHE_DIR = Path.home() / ".mm" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_cached(key: str, ttl_seconds: Optional[int] = None) -> Optional[Any]:
    """Get cached data if still valid.

    Args:
        key: Cache key (e.g., 'accounts', 'transactions')
        ttl_seconds: Time-to-live in seconds. If None, uses config default.

    Returns:
        Cached data if valid, None otherwise
    """
    if ttl_seconds is None:
        from cli.config import get_default
        ttl_seconds = get_default('cache.ttl_seconds', 300)

    cache_file = CACHE_DIR / f"{key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file) as f:
            cached = json.load(f)

        # Check expiry
        if time.time() - cached['timestamp'] > ttl_seconds:
            cache_file.unlink()  # Delete expired cache
            logger.debug(f"Cache expired for key: {key}")
            return None

        logger.debug(f"Cache hit for key: {key}")
        return cached['data']
    except Exception as e:
        logger.warning(f"Failed to read cache for {key}: {e}")
        # Delete corrupt cache file
        if cache_file.exists():
            cache_file.unlink()
        return None

def set_cached(key: str, data: Any) -> None:
    """Save data to cache.

    Args:
        key: Cache key
        data: Data to cache (must be JSON-serializable)
    """
    cache_file = CACHE_DIR / f"{key}.json"

    try:
        with open(cache_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'data': data
            }, f, default=str)
        logger.debug(f"Cached data for key: {key}")
    except Exception as e:
        logger.warning(f"Failed to cache data for {key}: {e}")

def clear_cache(key: Optional[str] = None) -> None:
    """Clear cached data.

    Args:
        key: Specific cache key to clear. If None, clears all cache.
    """
    if key:
        cache_file = CACHE_DIR / f"{key}.json"
        if cache_file.exists():
            cache_file.unlink()
            logger.info(f"Cleared cache for key: {key}")
    else:
        count = 0
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()
            count += 1
        logger.info(f"Cleared {count} cache files")

def is_cache_enabled() -> bool:
    """Check if caching is enabled in config."""
    from cli.config import get_default
    return get_default('cache.enabled', True)
