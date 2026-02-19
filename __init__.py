"""
Shared library for AI development projects.

This library provides common functionality across multiple projects including:
- LLM provider abstraction
- Observability and telemetry
- Memory and caching (Redis)
- Utilities for configuration and retry logic
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
