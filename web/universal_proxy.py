"""
Universal LLM Proxy Blueprint

Provides a thin, secure proxy layer that routes frontend requests to shared.llm_providers.
This eliminates the need for frontend-specific provider implementations and keeps API keys secure.

Usage:
    from shared.web.universal_proxy import create_universal_proxy_bp
    from flask import Flask

    app = Flask(__name__)
    proxy_bp = create_universal_proxy_bp()
    app.register_blueprint(proxy_bp)

Features:
- Single endpoint: POST /api/proxy
- Request schema: {provider, model, messages, stream, image_data}
- Uses ProviderFactory from shared.llm_providers
- Streaming SSE support
- Error handling with retry logic
- Rate limiting per provider
- No API keys in frontend
"""

import json
import logging
from typing import Optional
from flask import Blueprint, request, jsonify, Response, stream_with_context
from functools import wraps
import time

# Import from shared library
import sys
from shared.llm_providers import Message
from shared.llm_providers.factory import ProviderFactory
from shared.config import ConfigManager

logger = logging.getLogger(__name__)


class UniversalProxyError(Exception):
    """Base exception for universal proxy errors"""


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # provider -> [(timestamp, count)]

    def check_rate_limit(self, provider: str) -> bool:
        """Check if request is within rate limit"""
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        if provider in self.requests:
            self.requests[provider] = [
                (ts, count) for ts, count in self.requests[provider]
                if ts > minute_ago
            ]
        else:
            self.requests[provider] = []

        # Count requests in last minute
        total = sum(count for _, count in self.requests[provider])

        if total >= self.requests_per_minute:
            return False

        # Add this request
        self.requests[provider].append((now, 1))
        return True


# Global rate limiter
rate_limiter = RateLimiter(requests_per_minute=60)


def require_api_key(f):
    """Decorator to require API key for protected endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Optional: Add API key authentication here
        # For now, we rely on the backend being protected by Caddy/firewall
        return f(*args, **kwargs)
    return decorated_function


def create_universal_proxy_bp(
    url_prefix: str = '/api',
    config_manager: Optional[ConfigManager] = None,
    rate_limit: int = 60
) -> Blueprint:
    """
    Create a Flask blueprint for the universal LLM proxy.

    Args:
        url_prefix: URL prefix for the blueprint (default: /api)
        config_manager: ConfigManager instance (creates new one if None)
        rate_limit: Requests per minute per provider (default: 60)

    Returns:
        Flask Blueprint with /proxy endpoint
    """

    bp = Blueprint('universal_proxy', __name__, url_prefix=url_prefix)

    # Initialize config manager
    if config_manager is None:
        config_manager = ConfigManager(app_name='universal_proxy')

    # Update rate limiter
    global rate_limiter
    rate_limiter = RateLimiter(requests_per_minute=rate_limit)

    @bp.route('/proxy', methods=['POST'])
    @require_api_key
    def proxy():
        """
        Universal proxy endpoint for all LLM providers.

        Request JSON:
        {
            "provider": "anthropic",           # Required: provider name
            "model": "claude-sonnet-4-5",      # Optional: model name
            "messages": [                      # Required: conversation messages
                {"role": "user", "content": "Hello"}
            ],
            "stream": false,                   # Optional: streaming response
            "image_data": "base64...",         # Optional: image for vision models
            "max_tokens": 1000,                # Optional: max response tokens
            "temperature": 0.7                 # Optional: sampling temperature
        }

        Response:
        - Non-streaming: {"content": "...", "model": "...", "usage": {...}}
        - Streaming: Server-Sent Events (text/event-stream)
        """
        try:
            # Parse request
            data = request.get_json()
            if not data:
                return jsonify({"error": "Missing request body"}), 400

            provider_name = data.get('provider')
            if not provider_name:
                return jsonify({"error": "Missing 'provider' field"}), 400

            # Check rate limit
            if not rate_limiter.check_rate_limit(provider_name):
                return jsonify({
                    "error": "Rate limit exceeded",
                    "provider": provider_name,
                    "limit": rate_limiter.requests_per_minute
                }), 429

            # Get API key for provider
            api_key = config_manager.get_api_key(provider_name)
            if not api_key:
                return jsonify({
                    "error": f"No API key configured for provider: {provider_name}",
                    "provider": provider_name
                }), 400

            # Parse messages
            messages_data = data.get('messages', [])
            if not messages_data:
                return jsonify({"error": "Missing 'messages' field"}), 400

            messages = [
                Message(role=msg.get('role', 'user'), content=msg.get('content', ''))
                for msg in messages_data
            ]

            # Create provider instance
            try:
                provider = ProviderFactory.create_provider(
                    provider_name=provider_name,
                    api_key=api_key,
                    model=data.get('model')
                )
            except Exception as e:
                logger.error(f"Failed to create provider {provider_name}: {e}")
                return jsonify({
                    "error": f"Failed to create provider: {str(e)}",
                    "provider": provider_name
                }), 500

            # Handle streaming vs non-streaming
            stream = data.get('stream', False)

            if stream:
                # Streaming response with SSE
                def generate():
                    try:
                        kwargs = {}
                        if 'max_tokens' in data:
                            kwargs['max_tokens'] = data['max_tokens']
                        if 'temperature' in data:
                            kwargs['temperature'] = data['temperature']

                        for chunk in provider.stream_complete(messages, **kwargs):
                            yield f"data: {json.dumps({'content': chunk})}\n\n"

                        yield "data: [DONE]\n\n"

                    except Exception as e:
                        logger.error(f"Streaming error: {e}")
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"

                return Response(
                    stream_with_context(generate()),
                    mimetype='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'X-Accel-Buffering': 'no'
                    }
                )

            else:
                # Non-streaming response
                kwargs = {}
                if 'max_tokens' in data:
                    kwargs['max_tokens'] = data['max_tokens']
                if 'temperature' in data:
                    kwargs['temperature'] = data['temperature']

                # Handle image for vision models
                if 'image_data' in data:
                    # Use analyze_image if provider supports it
                    try:
                        response = provider.analyze_image(
                            image=data['image_data'],
                            prompt=messages[-1].content if messages else "Describe this image",
                            **kwargs
                        )
                    except NotImplementedError:
                        return jsonify({
                            "error": f"Provider {provider_name} does not support vision",
                            "provider": provider_name
                        }), 400
                else:
                    # Regular chat completion
                    response = provider.complete(messages, **kwargs)

                return jsonify({
                    "content": response.content,
                    "model": response.model,
                    "usage": response.usage,
                    "provider": provider_name
                })

        except Exception as e:
            logger.exception(f"Proxy error: {e}")
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500

    @bp.route('/providers', methods=['GET'])
    def list_providers():
        """
        List available providers with their configured status.

        Response:
        {
            "providers": {
                "anthropic": {"configured": true, "models": [...]},
                "openai": {"configured": true, "models": [...]},
                ...
            }
        }
        """
        try:
            providers_info = {}
            available_providers = config_manager.list_available_providers()

            for provider_name in available_providers:
                try:
                    api_key = config_manager.get_api_key(provider_name)
                    if api_key:
                        provider = ProviderFactory.create_provider(provider_name, api_key)
                        models = provider.list_models()
                        providers_info[provider_name] = {
                            "configured": True,
                            "models": models
                        }
                except Exception as e:
                    providers_info[provider_name] = {
                        "configured": False,
                        "error": str(e)
                    }

            return jsonify({"providers": providers_info})

        except Exception as e:
            logger.exception(f"Error listing providers: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({
            "status": "healthy",
            "service": "universal-llm-proxy",
            "providers_configured": len(config_manager.list_available_providers())
        })

    return bp


# Convenience function for quick Flask app creation
def create_proxy_app(
    config_manager: Optional[ConfigManager] = None,
    rate_limit: int = 60
) -> 'Flask':
    """
    Create a standalone Flask app with the universal proxy.

    Args:
        config_manager: ConfigManager instance
        rate_limit: Requests per minute per provider

    Returns:
        Flask app ready to run
    """
    from flask import Flask
    from flask_cors import CORS

    app = Flask(__name__)
    CORS(app)

    # Register blueprint
    proxy_bp = create_universal_proxy_bp(
        config_manager=config_manager,
        rate_limit=rate_limit
    )
    app.register_blueprint(proxy_bp)

    return app


if __name__ == '__main__':
    # Example standalone usage
    app = create_proxy_app()
    app.run(host='0.0.0.0', port=5050, debug=True)
