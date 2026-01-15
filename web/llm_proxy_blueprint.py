"""
Reusable Flask blueprint for LLM API proxy.

Provides a drop-in multi-provider LLM proxy using shared library providers.
Handles chat completions, image generation, and vision analysis.
"""

import os
import uuid
import logging
from typing import Optional
from flask import Blueprint, request, jsonify
from datetime import datetime

# Import shared library providers
import sys
sys.path.insert(0, '/home/coolhand/shared')
from llm_providers import Message
from llm_providers.anthropic_provider import AnthropicProvider
from llm_providers.openai_provider import OpenAIProvider
from llm_providers.xai_provider import XAIProvider


logger = logging.getLogger(__name__)


class LLMProxyBlueprint:
    """
    Multi-provider LLM API proxy blueprint.

    Usage:
        proxy = LLMProxyBlueprint(
            name="my_api",
            rate_limiter=rate_limiter,  # Optional
            default_provider="xai"
        )
        app.register_blueprint(proxy.blueprint, url_prefix='/api')
    """

    def __init__(
        self,
        name: str = "llm_proxy",
        rate_limiter=None,
        default_provider: str = "xai",
        enabled_providers: Optional[list] = None
    ):
        self.name = name
        self.rate_limiter = rate_limiter
        self.default_provider = default_provider
        self.blueprint = Blueprint(name, __name__)

        # Initialize providers
        self.providers = {}
        provider_classes = {
            'anthropic': (AnthropicProvider, 'ANTHROPIC_API_KEY'),
            'openai': (OpenAIProvider, 'OPENAI_API_KEY'),
            'xai': (XAIProvider, 'XAI_API_KEY'),
        }

        # Filter to enabled providers if specified
        if enabled_providers:
            provider_classes = {
                k: v for k, v in provider_classes.items()
                if k in enabled_providers
            }

        # Initialize each provider
        for provider_name, (provider_class, env_key) in provider_classes.items():
            api_key = os.getenv(env_key)
            if api_key:
                try:
                    self.providers[provider_name] = provider_class(api_key=api_key)
                    logger.info(f"✓ {provider_name} provider initialized")
                except Exception as e:
                    logger.warning(f"✗ {provider_name} provider failed: {e}")

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all API routes"""

        @self.blueprint.route('/chat/completions', methods=['POST'])
        def chat_completions():
            """Multi-provider chat completions endpoint"""
            # Rate limiting
            if self.rate_limiter and not self.rate_limiter.check_limit():
                return jsonify({"error": "Rate limit exceeded"}), 429

            try:
                data = request.get_json()

                # Validate required fields
                if not data or 'messages' not in data:
                    return jsonify({"error": "Missing required field: messages"}), 400

                # Extract provider
                provider_name = data.pop('provider', self.default_provider)

                if provider_name not in self.providers:
                    return jsonify({
                        "error": f"Unknown or disabled provider: {provider_name}",
                        "available_providers": list(self.providers.keys())
                    }), 400

                provider = self.providers[provider_name]

                # Convert messages to shared library format
                messages = [
                    Message(
                        role=msg.get('role', 'user'),
                        content=msg.get('content', '')
                    )
                    for msg in data['messages']
                ]

                # Extract parameters
                model = data.get('model')
                temperature = data.get('temperature')
                max_tokens = data.get('max_tokens')

                # Generate request ID
                request_id = str(uuid.uuid4())
                logger.info(f"Chat request {request_id}: {provider_name}/{model}")

                # Call shared library provider
                response = provider.complete(
                    messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                # Return OpenAI-compatible format
                result = {
                    "id": request_id,
                    "object": "chat.completion",
                    "created": int(datetime.now().timestamp()),
                    "model": response.model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response.content
                            },
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": response.usage
                }

                return jsonify(result)

            except Exception as e:
                logger.error(f"Chat completion error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.blueprint.route('/images/generations', methods=['POST'])
        def image_generation():
            """Image generation endpoint (OpenAI DALL-E and xAI Aurora)"""
            # Rate limiting
            if self.rate_limiter and not self.rate_limiter.check_limit():
                return jsonify({"error": "Rate limit exceeded"}), 429

            try:
                data = request.get_json()

                # Validate required fields
                if not data or 'prompt' not in data:
                    return jsonify({"error": "Missing required field: prompt"}), 400

                # Extract provider
                provider_name = data.pop('provider', 'xai')

                if provider_name not in self.providers:
                    return jsonify({"error": f"Unknown provider: {provider_name}"}), 400

                provider = self.providers[provider_name]

                # Check if provider supports image generation
                if not hasattr(provider, 'generate_image'):
                    return jsonify({
                        "error": f"{provider_name} does not support image generation"
                    }), 400

                # Extract parameters
                prompt = data['prompt']
                model = data.get('model')
                size = data.get('size', '1024x1024')

                # Generate request ID
                request_id = str(uuid.uuid4())
                logger.info(f"Image generation request {request_id}: {provider_name}")

                # Call shared library provider
                response = provider.generate_image(
                    prompt,
                    model=model,
                    size=size
                )

                # Return OpenAI-compatible format
                result = {
                    "created": int(datetime.now().timestamp()),
                    "data": [
                        {
                            "b64_json": response.image_data,
                            "revised_prompt": response.revised_prompt
                        }
                    ]
                }

                return jsonify(result)

            except Exception as e:
                logger.error(f"Image generation error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.blueprint.route('/providers', methods=['GET'])
        def list_providers():
            """List available providers"""
            provider_info = {}

            for name, provider in self.providers.items():
                try:
                    models = provider.list_models()
                    provider_info[name] = {
                        "status": "available",
                        "models": models
                    }
                except Exception as e:
                    provider_info[name] = {
                        "status": "error",
                        "error": str(e)
                    }

            return jsonify({
                "default_provider": self.default_provider,
                "providers": provider_info
            })

        @self.blueprint.route('/test', methods=['GET'])
        def test_provider():
            """Test a specific provider"""
            provider_name = request.args.get('provider', self.default_provider)

            if provider_name not in self.providers:
                return jsonify({"error": f"Unknown provider: {provider_name}"}), 400

            try:
                provider = self.providers[provider_name]
                models = provider.list_models()

                return jsonify({
                    "status": "ok",
                    "provider": provider_name,
                    "models": models
                })

            except Exception as e:
                return jsonify({
                    "status": "error",
                    "provider": provider_name,
                    "error": str(e)
                }), 500


def create_llm_proxy_app(
    name: str = "LLM Proxy",
    port: int = 8000,
    rate_limit: int = 20,
    default_provider: str = "xai"
):
    """
    Create a complete Flask app with LLM proxy.

    Example:
        app = create_llm_proxy_app(
            name="My API",
            port=8000,
            rate_limit=20
        )

        if __name__ == '__main__':
            app.run(port=8000)
    """
    from flask import Flask
    from .cors_config import setup_cors
    from .health import create_health_endpoint
    from .rate_limit import RateLimiter

    app = Flask(name)

    # Setup CORS
    setup_cors(app)

    # Setup rate limiter
    rate_limiter = RateLimiter(requests_per_minute=rate_limit)

    # Create LLM proxy blueprint
    proxy = LLMProxyBlueprint(
        name="llm_proxy",
        rate_limiter=rate_limiter,
        default_provider=default_provider
    )

    # Register blueprint
    app.register_blueprint(proxy.blueprint, url_prefix='/api')

    # Add health check
    create_health_endpoint(app, name, "1.0.0")

    logger.info(f"✓ {name} initialized on port {port}")

    return app
