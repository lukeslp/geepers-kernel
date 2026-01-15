"""
API Authentication Module

Centralized authentication and rate limiting for all dr.eamer.dev APIs

Usage:
    from api_auth import AuthManager, require_api_key

    # Initialize
    auth_manager = AuthManager()

    # In Flask app
    @app.route('/api/search')
    @require_api_key(auth_manager, 'blissAPI')
    def search():
        # Access: request.api_key_id, request.api_tier, request.api_authenticated
        ...

CLI Tools:
    python -m api_auth.cli generate --prefix bliss --email user@example.com --tier basic
    python -m api_auth.cli list
    python -m api_auth.cli revoke <key_id>
    python -m api_auth.cli usage --api blissAPI --days 7
    python -m api_auth.cli stats

Author: Luke Steuber
License: MIT
"""

from .auth_manager import AuthManager, require_api_key

__all__ = ['AuthManager', 'require_api_key']
__version__ = '1.0.0'
