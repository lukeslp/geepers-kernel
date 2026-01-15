#!/usr/bin/env python3
"""
API Authentication Manager

Purpose: Centralized authentication and rate limiting for all dr.eamer.dev APIs
Primary Functions:
- API key generation with bcrypt hashing
- API key validation
- Token bucket rate limiting
- Usage logging and analytics

Primary Classes:
- AuthManager: Main authentication manager

Usage:
    from api_auth import AuthManager

    auth_manager = AuthManager(db_path="/home/coolhand/data/api_auth.db")

    # Generate new API key
    key_info = auth_manager.generate_api_key("bliss", "user@example.com", "basic")
    print(f"API Key (save this!): {key_info['api_key']}")

    # Validate API key
    is_valid, key_info = auth_manager.validate_api_key(api_key)

    # Check rate limit
    allowed, remaining = auth_manager.check_rate_limit(key_id, "blissAPI", "basic")

    # Log usage
    auth_manager.log_usage(key_id, "blissAPI", "/api/search", "GET", 200, 45, True, "192.168.1.1")

Author: Luke Steuber
License: MIT
"""

import sqlite3
import bcrypt
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
from contextlib import contextmanager
import os

class AuthManager:
    """Manages API authentication, rate limiting, and usage tracking"""

    def __init__(self, db_path: str = None):
        """
        Initialize AuthManager

        Args:
            db_path: Path to SQLite database (default: /home/coolhand/data/api_auth.db)
        """
        if db_path is None:
            db_path = "/home/coolhand/data/api_auth.db"

        self.db_path = db_path
        self._ensure_database()

    def _ensure_database(self):
        """Ensure database and schema exist"""
        # Create data directory if needed
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Create database and schema
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path) as f:
                schema_sql = f.read()

            with self._get_connection() as conn:
                conn.executescript(schema_sql)

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def generate_api_key(
        self,
        prefix: str,
        user_email: str,
        tier: str = "basic",
        api_name: Optional[str] = None,
        expires_days: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a new API key

        Args:
            prefix: Key prefix (e.g., "bliss" becomes "sk_bliss_...")
            user_email: User's email address
            tier: Rate limit tier (free, basic, premium)
            api_name: Optional API name restriction
            expires_days: Optional expiration in days from now
            notes: Optional notes about the key

        Returns:
            Dict with api_key (ONLY SHOWN ONCE), key_id, key_prefix, tier

        WARNING: The full API key is ONLY returned once. It cannot be retrieved later.
        """
        # Generate random secret (32 bytes = 43 base64 chars)
        secret = secrets.token_urlsafe(32)

        # Format: sk_{prefix}_{secret}
        api_key = f"sk_{prefix}_{secret}"
        key_prefix = f"sk_{prefix}_{secret[:8]}..."

        # Hash the full key with bcrypt
        key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Generate UUID for key_id
        key_id = str(uuid.uuid4())

        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()

        # Insert into database
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO api_keys (key_id, key_hash, key_prefix, user_email, tier, api_name, expires_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (key_id, key_hash, key_prefix, user_email, tier, api_name, expires_at, notes))

        return {
            "api_key": api_key,  # ONLY SHOWN ONCE
            "key_id": key_id,
            "key_prefix": key_prefix,
            "user_email": user_email,
            "tier": tier,
            "api_name": api_name,
            "expires_at": expires_at,
            "message": "Save this API key securely. It cannot be retrieved later."
        }

    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate an API key

        Args:
            api_key: Full API key to validate

        Returns:
            Tuple of (is_valid, key_info_dict or None)
        """
        if not api_key or not api_key.startswith("sk_"):
            return False, None

        with self._get_connection() as conn:
            # Get all active keys (we need to check bcrypt hash for each)
            cursor = conn.execute("""
                SELECT key_id, key_hash, key_prefix, user_email, tier, api_name, requests_per_minute
                FROM active_keys
            """)

            for row in cursor:
                # Check if bcrypt hash matches
                if bcrypt.checkpw(api_key.encode('utf-8'), row['key_hash'].encode('utf-8')):
                    # Valid key! Update last_used_at
                    conn.execute("""
                        UPDATE api_keys
                        SET last_used_at = datetime('now')
                        WHERE key_id = ?
                    """, (row['key_id'],))

                    return True, {
                        "key_id": row['key_id'],
                        "key_prefix": row['key_prefix'],
                        "user_email": row['user_email'],
                        "tier": row['tier'],
                        "api_name": row['api_name'],
                        "requests_per_minute": row['requests_per_minute']
                    }

        return False, None

    def check_rate_limit(
        self,
        key_id: Optional[str],
        api_name: str,
        tier: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit

        Uses token bucket algorithm with per-minute windows.

        Args:
            key_id: API key ID (None for free tier)
            api_name: Name of the API being accessed
            tier: Rate limit tier (free, basic, premium)
            ip_address: IP address (required for free tier)

        Returns:
            Tuple of (allowed, remaining_requests_this_minute)
        """
        # Get rate limit for tier
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT requests_per_minute FROM rate_limit_tiers WHERE tier = ?
            """, (tier,))
            row = cursor.fetchone()

            if not row:
                # Unknown tier, default to free
                limit = 10
            else:
                limit = row['requests_per_minute']

            # Get current minute window (truncate to minute)
            now = datetime.utcnow()
            window_start = now.replace(second=0, microsecond=0).isoformat()

            # Get or create rate limit record
            if key_id:
                # Authenticated user
                cursor = conn.execute("""
                    INSERT INTO rate_limits (key_id, api_name, window_start, request_count)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(key_id, api_name, window_start)
                    DO UPDATE SET request_count = request_count + 1
                    RETURNING request_count
                """, (key_id, api_name, window_start))
            else:
                # Free tier (IP-based)
                if not ip_address:
                    # No IP provided, reject
                    return False, 0

                cursor = conn.execute("""
                    INSERT INTO rate_limits (ip_address, api_name, window_start, request_count)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(ip_address, api_name, window_start)
                    DO UPDATE SET request_count = request_count + 1
                    RETURNING request_count
                """, (ip_address, api_name, window_start))

            row = cursor.fetchone()
            request_count = row['request_count']

            # Clean up old windows (older than 5 minutes)
            cleanup_time = (now - timedelta(minutes=5)).isoformat()
            conn.execute("""
                DELETE FROM rate_limits WHERE window_start < ?
            """, (cleanup_time,))

            # Check if allowed
            allowed = request_count <= limit
            remaining = max(0, limit - request_count)

            return allowed, remaining

    def log_usage(
        self,
        key_id: Optional[str],
        api_name: str,
        endpoint: str,
        method: str = "GET",
        status_code: int = 200,
        response_time_ms: Optional[int] = None,
        cache_hit: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log API usage for analytics

        Args:
            key_id: API key ID (None for free tier)
            api_name: Name of the API
            endpoint: Endpoint accessed (e.g., "/api/search")
            method: HTTP method
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            cache_hit: Whether response came from cache
            ip_address: Client IP address
            user_agent: Client user agent
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO api_usage (
                    key_id, api_name, endpoint, method, status_code,
                    response_time_ms, cache_hit, ip_address, user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key_id, api_name, endpoint, method, status_code,
                response_time_ms, int(cache_hit), ip_address, user_agent
            ))

    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key

        Args:
            key_id: API key ID to revoke

        Returns:
            True if key was revoked, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE api_keys SET is_active = 0 WHERE key_id = ?
            """, (key_id,))
            return cursor.rowcount > 0

    def list_keys(self, user_email: Optional[str] = None, active_only: bool = True) -> list:
        """
        List API keys

        Args:
            user_email: Filter by user email
            active_only: Only show active keys

        Returns:
            List of key info dicts
        """
        with self._get_connection() as conn:
            if active_only:
                query = "SELECT * FROM active_keys"
                params = []
                if user_email:
                    query += " WHERE user_email = ?"
                    params.append(user_email)
            else:
                query = """
                    SELECT key_id, key_prefix, user_email, tier, api_name,
                           created_at, last_used_at, expires_at, is_active
                    FROM api_keys
                """
                if user_email:
                    query += " WHERE user_email = ?"
                    params = [user_email]
                else:
                    params = []

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_usage_stats(self, api_name: Optional[str] = None, days: int = 7) -> list:
        """
        Get usage statistics

        Args:
            api_name: Filter by API name
            days: Number of days to look back

        Returns:
            List of usage stat dicts
        """
        with self._get_connection() as conn:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

            query = """
                SELECT
                    api_name,
                    endpoint,
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits,
                    ROUND(AVG(response_time_ms), 2) as avg_response_ms,
                    COUNT(DISTINCT key_id) as unique_users,
                    COUNT(DISTINCT DATE(timestamp)) as active_days
                FROM api_usage
                WHERE timestamp >= ?
            """

            params = [cutoff]
            if api_name:
                query += " AND api_name = ?"
                params.append(api_name)

            query += " GROUP BY api_name, endpoint ORDER BY total_requests DESC"

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


def require_api_key(auth_manager: AuthManager, api_name: str):
    """
    Flask decorator for API key authentication

    Usage:
        @app.route('/api/search')
        @require_api_key(auth_manager, 'blissAPI')
        def search():
            # Access key info via request.api_key_id, request.api_tier, etc.
            ...

    Free tier (no API key) is allowed but with lower rate limits.
    Authenticated users get higher rate limits.
    """
    from flask import request, jsonify
    from functools import wraps
    import time

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Start timing
            start_time = time.time()

            # Extract API key from Authorization header
            auth_header = request.headers.get('Authorization', '')
            api_key = None
            key_id = None
            tier = 'free'

            if auth_header.startswith('Bearer '):
                api_key = auth_header[7:]  # Remove "Bearer " prefix
                is_valid, key_info = auth_manager.validate_api_key(api_key)

                if is_valid:
                    key_id = key_info['key_id']
                    tier = key_info['tier']

                    # Check if key is restricted to specific API
                    if key_info['api_name'] and key_info['api_name'] != api_name:
                        return jsonify({
                            "error": "API key not authorized for this API",
                            "api_name": api_name
                        }), 403
                else:
                    # Invalid API key provided
                    return jsonify({
                        "error": "Invalid API key",
                        "message": "The provided API key is not valid"
                    }), 401

            # Check rate limit
            ip_address = request.remote_addr
            allowed, remaining = auth_manager.check_rate_limit(key_id, api_name, tier, ip_address)

            if not allowed:
                # Rate limit exceeded
                auth_manager.log_usage(
                    key_id, api_name, request.path, request.method,
                    429, None, False, ip_address, request.user_agent.string
                )
                return jsonify({
                    "error": "Rate limit exceeded",
                    "tier": tier,
                    "limit": f"{tier} tier allows limited requests per minute",
                    "message": "Upgrade to a higher tier or wait before retrying"
                }), 429

            # Add rate limit info to response headers
            response_headers = {
                'X-RateLimit-Tier': tier,
                'X-RateLimit-Remaining': str(remaining)
            }

            # Attach key info to request for use in endpoint
            request.api_key_id = key_id
            request.api_tier = tier
            request.api_authenticated = (key_id is not None)

            # Call the actual endpoint
            try:
                response = f(*args, **kwargs)

                # Calculate response time
                response_time_ms = int((time.time() - start_time) * 1000)

                # Log usage
                status_code = 200
                cache_hit = False
                if hasattr(response, 'status_code'):
                    status_code = response.status_code
                if hasattr(request, 'cache_hit'):
                    cache_hit = request.cache_hit

                auth_manager.log_usage(
                    key_id, api_name, request.path, request.method,
                    status_code, response_time_ms, cache_hit,
                    ip_address, request.user_agent.string
                )

                # Add rate limit headers to response
                if hasattr(response, 'headers'):
                    for header, value in response_headers.items():
                        response.headers[header] = value

                return response

            except Exception as e:
                # Log error
                response_time_ms = int((time.time() - start_time) * 1000)
                auth_manager.log_usage(
                    key_id, api_name, request.path, request.method,
                    500, response_time_ms, False,
                    ip_address, request.user_agent.string
                )
                raise e

        return decorated_function
    return decorator


if __name__ == "__main__":
    # Test the auth manager
    print("Testing AuthManager...")

    # Create test database
    test_db = "/tmp/test_api_auth.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    auth = AuthManager(test_db)

    # Generate test key
    print("\n1. Generating API key...")
    key_info = auth.generate_api_key("test", "test@example.com", "basic")
    print(f"   Key: {key_info['key_prefix']}")
    print(f"   Full key: {key_info['api_key']}")

    # Validate key
    print("\n2. Validating API key...")
    is_valid, info = auth.validate_api_key(key_info['api_key'])
    print(f"   Valid: {is_valid}")
    print(f"   Tier: {info['tier']}")

    # Check rate limit
    print("\n3. Checking rate limits...")
    for i in range(5):
        allowed, remaining = auth.check_rate_limit(info['key_id'], "testAPI", "basic")
        print(f"   Request {i+1}: Allowed={allowed}, Remaining={remaining}")

    # Log usage
    print("\n4. Logging usage...")
    auth.log_usage(info['key_id'], "testAPI", "/api/test", "GET", 200, 45, True, "127.0.0.1")

    # Get stats
    print("\n5. Usage stats:")
    stats = auth.get_usage_stats(days=1)
    for stat in stats:
        print(f"   {stat['api_name']}{stat['endpoint']}: {stat['total_requests']} requests")

    print("\n✓ All tests passed!")
