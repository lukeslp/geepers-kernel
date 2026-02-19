"""
geepers-kernel exception hierarchy.

Catch GeepersError to handle any library error.
Catch specific subclasses for fine-grained handling.

Author: Luke Steuber
"""


class GeepersError(Exception):
    """Base for all geepers-kernel errors."""


# Provider errors

class ProviderError(GeepersError):
    """An LLM provider call failed."""

    def __init__(self, message: str, provider: str = "", model: str = ""):
        super().__init__(message)
        self.provider = provider
        self.model = model


class RateLimitError(ProviderError):
    """Provider returned a rate limit / quota error."""

    def __init__(self, message: str, provider: str = "", model: str = "", retry_after: float = 0.0):
        super().__init__(message, provider=provider, model=model)
        self.retry_after = retry_after  # seconds, 0 = unknown


class AuthenticationError(ProviderError):
    """API key missing, invalid, or expired."""


class ProviderUnavailableError(ProviderError):
    """Provider endpoint is down or returning 5xx."""


class ModelNotFoundError(ProviderError):
    """Requested model doesn't exist or isn't accessible."""


# Orchestration errors

class OrchestrationError(GeepersError):
    """A multi-agent workflow failed."""


class SubtaskError(OrchestrationError):
    """An individual subtask within a workflow failed."""

    def __init__(self, message: str, subtask_id: str = ""):
        super().__init__(message)
        self.subtask_id = subtask_id


class WorkflowTimeoutError(OrchestrationError):
    """Workflow exceeded its time limit."""


# Data fetching errors

class DataFetchingError(GeepersError):
    """A data client call failed."""

    def __init__(self, message: str, client: str = ""):
        super().__init__(message)
        self.client = client


class DataSourceUnavailableError(DataFetchingError):
    """External data source is unreachable."""


# Configuration errors

class ConfigurationError(GeepersError):
    """Missing or invalid configuration."""


class MissingApiKeyError(ConfigurationError):
    """Required API key is not set."""

    def __init__(self, provider: str):
        super().__init__(f"No API key configured for provider: {provider}")
        self.provider = provider
