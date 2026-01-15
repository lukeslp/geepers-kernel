"""
Cache & Memory MCP Server

Exposes shared.memory caching capabilities through MCP protocol.

Tools provided:
- cache_get: Retrieve cached value
- cache_set: Store value with TTL
- cache_delete: Delete key
- cache_increment: Increment counter
- cache_list_keys: List keys by pattern
- cache_exists: Check if key exists
- cache_expire: Set TTL on existing key

Resources provided:
- cache://stats: Cache statistics
- cache://keys/{namespace}: List keys in namespace
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import from shared library
import sys
sys.path.insert(0, '/home/coolhand/shared')
from memory import RedisManager
from config import ConfigManager

logger = logging.getLogger(__name__)


class CacheServer:
    """
    MCP server for caching and memory management.

    Exposes RedisManager capabilities through MCP protocol.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize cache MCP server.

        Args:
            config_manager: ConfigManager instance (creates new one if None)
        """
        self.config = config_manager or ConfigManager(app_name='mcp_cache')

        # Initialize Redis client (lazy loading)
        self._redis_client = None

    def get_redis_client(self) -> RedisManager:
        """Get or create Redis client."""
        if self._redis_client is None:
            try:
                self._redis_client = RedisManager()
                logger.info("Redis client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                raise
        return self._redis_client

    # -------------------------------------------------------------------------
    # MCP Tools - Basic Cache Operations
    # -------------------------------------------------------------------------

    def tool_cache_get(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: cache_get

        Retrieve cached value.

        Arguments:
            key (str): Cache key
            namespace (str, optional): Key namespace prefix

        Returns:
            {success: bool, value: Any, found: bool}
        """
        try:
            key = arguments.get('key')
            if not key:
                return {
                    "success": False,
                    "error": "Missing required argument: key"
                }

            # Add namespace prefix if provided
            namespace = arguments.get('namespace')
            if namespace:
                key = f"{namespace}:{key}"

            redis = self.get_redis_client()
            value = redis.get(key)

            return {
                "success": True,
                "value": value,
                "found": value is not None,
                "key": key
            }

        except Exception as e:
            logger.exception(f"Error in cache_get: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_cache_set(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: cache_set

        Store value with optional TTL.

        Arguments:
            key (str): Cache key
            value (any): Value to cache
            ttl (int, optional): Time-to-live in seconds
            namespace (str, optional): Key namespace prefix

        Returns:
            {success: bool, key: str, ttl: int}
        """
        try:
            key = arguments.get('key')
            value = arguments.get('value')

            if not key or value is None:
                return {
                    "success": False,
                    "error": "Missing required arguments: key and value"
                }

            # Add namespace prefix if provided
            namespace = arguments.get('namespace')
            if namespace:
                key = f"{namespace}:{key}"

            redis = self.get_redis_client()
            ttl = arguments.get('ttl')

            result = redis.set(key, value, ttl=ttl)

            return {
                "success": bool(result),
                "key": key,
                "ttl": ttl,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.exception(f"Error in cache_set: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_cache_delete(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: cache_delete

        Delete key from cache.

        Arguments:
            key (str): Cache key
            namespace (str, optional): Key namespace prefix

        Returns:
            {success: bool, deleted: bool}
        """
        try:
            key = arguments.get('key')
            if not key:
                return {
                    "success": False,
                    "error": "Missing required argument: key"
                }

            # Add namespace prefix if provided
            namespace = arguments.get('namespace')
            if namespace:
                key = f"{namespace}:{key}"

            redis = self.get_redis_client()
            deleted = redis.delete(key)

            return {
                "success": True,
                "deleted": deleted,
                "key": key
            }

        except Exception as e:
            logger.exception(f"Error in cache_delete: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_cache_increment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: cache_increment

        Increment counter.

        Arguments:
            key (str): Cache key
            amount (int, optional): Amount to increment (default: 1)
            namespace (str, optional): Key namespace prefix

        Returns:
            {success: bool, new_value: int}
        """
        try:
            key = arguments.get('key')
            if not key:
                return {
                    "success": False,
                    "error": "Missing required argument: key"
                }

            # Add namespace prefix if provided
            namespace = arguments.get('namespace')
            if namespace:
                key = f"{namespace}:{key}"

            redis = self.get_redis_client()
            amount = arguments.get('amount', 1)

            new_value = redis.increment(key, amount)

            return {
                "success": True,
                "new_value": new_value,
                "key": key
            }

        except Exception as e:
            logger.exception(f"Error in cache_increment: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_cache_exists(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: cache_exists

        Check if key exists.

        Arguments:
            key (str): Cache key
            namespace (str, optional): Key namespace prefix

        Returns:
            {success: bool, exists: bool}
        """
        try:
            key = arguments.get('key')
            if not key:
                return {
                    "success": False,
                    "error": "Missing required argument: key"
                }

            # Add namespace prefix if provided
            namespace = arguments.get('namespace')
            if namespace:
                key = f"{namespace}:{key}"

            redis = self.get_redis_client()
            exists = redis.exists(key)

            return {
                "success": True,
                "exists": exists,
                "key": key
            }

        except Exception as e:
            logger.exception(f"Error in cache_exists: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_cache_expire(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: cache_expire

        Set TTL on existing key.

        Arguments:
            key (str): Cache key
            ttl (int): Time-to-live in seconds
            namespace (str, optional): Key namespace prefix

        Returns:
            {success: bool, expired: bool}
        """
        try:
            key = arguments.get('key')
            ttl = arguments.get('ttl')

            if not key or ttl is None:
                return {
                    "success": False,
                    "error": "Missing required arguments: key and ttl"
                }

            # Add namespace prefix if provided
            namespace = arguments.get('namespace')
            if namespace:
                key = f"{namespace}:{key}"

            redis = self.get_redis_client()
            expired = redis.expire(key, ttl)

            return {
                "success": True,
                "expired": expired,
                "key": key,
                "ttl": ttl
            }

        except Exception as e:
            logger.exception(f"Error in cache_expire: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_cache_list_keys(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: cache_list_keys

        List keys matching pattern.

        Arguments:
            pattern (str, optional): Key pattern (default: *)
            namespace (str, optional): Key namespace prefix
            limit (int, optional): Max keys to return (default: 100)

        Returns:
            {success: bool, keys: List[str], count: int}
        """
        try:
            redis = self.get_redis_client()

            pattern = arguments.get('pattern', '*')
            namespace = arguments.get('namespace')

            if namespace:
                pattern = f"{namespace}:{pattern}"

            # Redis doesn't have a built-in limit, so we'll use SCAN
            # For simplicity, using keys() with pattern
            # In production, should use SCAN for large datasets
            try:
                keys = list(redis.client.scan_iter(match=pattern, count=arguments.get('limit', 100)))
            except:
                # Fallback if scan_iter not available
                keys = [k for k in redis.client.keys(pattern)]

            # Limit results
            limit = arguments.get('limit', 100)
            keys = keys[:limit]

            return {
                "success": True,
                "keys": keys,
                "count": len(keys),
                "pattern": pattern
            }

        except Exception as e:
            logger.exception(f"Error in cache_list_keys: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Resources
    # -------------------------------------------------------------------------

    def resource_cache_stats(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: cache://stats

        Returns cache statistics.

        Args:
            uri: Resource URI ("cache://stats")

        Returns:
            Cache statistics
        """
        try:
            redis = self.get_redis_client()

            # Get Redis INFO
            info = redis.client.info()

            stats = {
                "uri": uri,
                "connected": True,
                "redis_version": info.get('redis_version', 'unknown'),
                "used_memory": info.get('used_memory_human', 'unknown'),
                "total_keys": info.get('db0', {}).get('keys', 0) if 'db0' in info else 0,
                "uptime_seconds": info.get('uptime_in_seconds', 0),
                "connected_clients": info.get('connected_clients', 0),
                "timestamp": datetime.utcnow().isoformat()
            }

            return stats

        except Exception as e:
            logger.exception(f"Error in resource_cache_stats: {e}")
            return {
                "uri": uri,
                "connected": False,
                "error": str(e)
            }

    def resource_cache_keys(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: cache://keys/{namespace}

        Returns keys in a namespace.

        Args:
            uri: Resource URI (e.g., "cache://keys/user_prefs")

        Returns:
            Keys list
        """
        try:
            # Parse URI: cache://keys/{namespace}
            parts = uri.replace('cache://keys/', '')
            namespace = parts if parts else '*'

            redis = self.get_redis_client()

            # List keys with namespace prefix
            pattern = f"{namespace}:*" if namespace != '*' else '*'
            keys = list(redis.client.scan_iter(match=pattern, count=100))[:100]

            return {
                "uri": uri,
                "namespace": namespace,
                "keys": keys,
                "count": len(keys)
            }

        except Exception as e:
            logger.exception(f"Error in resource_cache_keys: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Server Interface
    # -------------------------------------------------------------------------

    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP tools manifest.

        Returns:
            List of tool definitions
        """
        return [
            {
                "name": "cache_get",
                "description": "Retrieve cached value",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Cache key"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Key namespace prefix (optional)"
                        }
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "cache_set",
                "description": "Store value with optional TTL",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Cache key"
                        },
                        "value": {
                            "description": "Value to cache (any type)"
                        },
                        "ttl": {
                            "type": "integer",
                            "description": "Time-to-live in seconds (optional)"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Key namespace prefix (optional)"
                        }
                    },
                    "required": ["key", "value"]
                }
            },
            {
                "name": "cache_delete",
                "description": "Delete key from cache",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Cache key"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Key namespace prefix (optional)"
                        }
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "cache_increment",
                "description": "Increment counter",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Cache key"
                        },
                        "amount": {
                            "type": "integer",
                            "description": "Amount to increment (default: 1)"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Key namespace prefix (optional)"
                        }
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "cache_exists",
                "description": "Check if key exists",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Cache key"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Key namespace prefix (optional)"
                        }
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "cache_expire",
                "description": "Set TTL on existing key",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Cache key"
                        },
                        "ttl": {
                            "type": "integer",
                            "description": "Time-to-live in seconds"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Key namespace prefix (optional)"
                        }
                    },
                    "required": ["key", "ttl"]
                }
            },
            {
                "name": "cache_list_keys",
                "description": "List keys matching pattern",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Key pattern (default: *)"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Key namespace prefix (optional)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max keys to return (default: 100)"
                        }
                    }
                }
            }
        ]

    def get_resources_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP resources manifest.

        Returns:
            List of resource templates
        """
        return [
            {
                "uri": "cache://stats",
                "name": "Cache Statistics",
                "description": "Redis cache statistics and health",
                "mimeType": "application/json"
            },
            {
                "uri": "cache://keys/{namespace}",
                "name": "Cache Keys List",
                "description": "List keys in a namespace",
                "mimeType": "application/json"
            }
        ]

