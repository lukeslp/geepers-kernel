"""
geepers-kernel — core infrastructure for LLM-powered multi-agent systems.

Provides:
- 14 LLM providers (Anthropic, OpenAI, xAI, Mistral, Cohere, Gemini, and more)
- Dream Cascade and Dream Swarm orchestrators for multi-agent workflows
- 18 structured data API clients (arXiv, Census, GitHub, NASA, Wikipedia, ...)
- MCP server exposing tools via HTTP/SSE (port 5060)
- Flask web utilities: blueprints, auth, CORS, SSE streaming
- Unified exception hierarchy (GeepersError and subclasses)
- Cost tracking and observability for all LLM calls
"""

__version__ = "1.1.0"

from .exceptions import (
    GeepersError,
    ProviderError, RateLimitError, AuthenticationError,
    ProviderUnavailableError, ModelNotFoundError,
    OrchestrationError, SubtaskError, WorkflowTimeoutError,
    DataFetchingError, DataSourceUnavailableError,
    ConfigurationError, MissingApiKeyError,
)

__all__ = [
    "GeepersError",
    "ProviderError", "RateLimitError", "AuthenticationError",
    "ProviderUnavailableError", "ModelNotFoundError",
    "OrchestrationError", "SubtaskError", "WorkflowTimeoutError",
    "DataFetchingError", "DataSourceUnavailableError",
    "ConfigurationError", "MissingApiKeyError",
]
