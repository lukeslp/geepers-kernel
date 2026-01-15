"""
CORS configuration utilities for Flask applications.

Provides standardized CORS setup for dr.eamer.dev domain and localhost.
"""

from flask import Flask
from flask_cors import CORS


def setup_cors(app: Flask, additional_origins: list = None):
    """
    Setup CORS for standard dr.eamer.dev configuration.

    Args:
        app: Flask application instance
        additional_origins: Optional list of additional allowed origins

    Returns:
        Configured Flask app
    """
    default_origins = [
        "https://dr.eamer.dev",
        "https://*.dr.eamer.dev",
        "https://d.reamwalker.com",
        "https://*.reamwalker.com",
        "https://d.reamwalk.com",
        "https://*.reamwalk.com",
        "http://localhost:*",
        "http://127.0.0.1:*",
        "file://*"
    ]

    if additional_origins:
        default_origins.extend(additional_origins)

    CORS(app, resources={
        r"/api/*": {
            "origins": default_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True,
            "expose_headers": ["Content-Range", "X-Content-Range"],
            "max_age": 3600
        }
    }, supports_credentials=True)

    # Add explicit OPTIONS handler for preflight requests
    @app.after_request
    def after_request(response):
        """Handle CORS headers for all responses"""
        from flask import request
        origin = request.headers.get('Origin')

        # Check if origin is from our allowed domains
        if origin and any(
            origin.startswith(prefix) for prefix in [
                'https://dr.eamer.dev',
                'https://d.reamwalker.com',
                'https://d.reamwalk.com',
                'http://localhost',
                'http://127.0.0.1'
            ]
        ):
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Max-Age', '3600')

        return response

    return app
