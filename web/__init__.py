"""
Shared web utilities and Flask components.

Provides reusable Flask blueprints, middleware, and utilities for
building API proxies and web services.
"""

from .rate_limit import RateLimiter
from .cors_config import setup_cors
from .health import create_health_endpoint
from .llm_proxy_blueprint import LLMProxyBlueprint, create_llm_proxy_app
from .vision_service import (
    decode_image_from_request,
    create_success_response,
    create_error_response,
    truncate_text,
    validate_image_size,
)
from .universal_proxy import create_universal_proxy_bp, create_proxy_app
from .dreamwalker import create_app as create_dreamwalker_app
from .auth import (
    get_bearer_token,
    require_api_token,
    generate_signed_token,
    verify_signed_token,
)
from .middleware import (
    register_request_logging,
    register_error_handlers,
    add_correlation_id,
)

__all__ = [
    'RateLimiter',
    'setup_cors',
    'create_health_endpoint',
    'LLMProxyBlueprint',
    'create_llm_proxy_app',
    'decode_image_from_request',
    'create_success_response',
    'create_error_response',
    'truncate_text',
    'validate_image_size',
    'create_universal_proxy_bp',
    'create_proxy_app',
    'create_dreamwalker_app',
    'get_bearer_token',
    'require_api_token',
    'generate_signed_token',
    'verify_signed_token',
    'register_request_logging',
    'register_error_handlers',
    'add_correlation_id',
]
