"""
Snippet for the provider factory pattern and base provider interface.
Demonstrates how to implement a provider system for multi-LLM support.
"""

from abc import ABC, abstractmethod
from typing import Dict, Generator, List, Optional, Any, Union
import logging
import importlib
import os

# Configure logging
logger = logging.getLogger(__name__)

class BaseProvider(ABC):
    """
    Base class for all AI API providers.
    
    This abstract class defines the interface that all provider implementations
    must follow to ensure consistent behavior across different AI services.
    """
    
    @abstractmethod
    def __init__(self, api_key: str):
        """
        Initialize the provider with an API key.
        
        Args:
            api_key: The API key for authentication with the provider's service
        """
        self.api_key = api_key
    
    @abstractmethod
    def list_models(self, **kwargs) -> List[Dict[str, Any]]:
        """
        List available models from this provider.
        
        Args:
            **kwargs: Additional provider-specific parameters
            
        Returns:
            List of model objects containing at minimum 'id' and 'name' fields
        """
        raise NotImplementedError("Subclasses must implement list_models")
    
    @abstractmethod
    def chat_completion(self, prompt: str, model: str, **kwargs) -> Dict[str, Any]:
        """
        Get a chat completion from the provider.
        
        Args:
            prompt: The user's message
            model: The model to use
            **kwargs: Additional parameters like temperature, max_tokens, etc.
            
        Returns:
            Dictionary containing the completion response
        """
        raise NotImplementedError("Subclasses must implement chat_completion")
    
    @abstractmethod
    def stream_chat_completion(self, prompt: str, model: str, **kwargs) -> Generator[str, None, None]:
        """
        Stream a chat completion from the provider.
        
        Args:
            prompt: The user's message
            model: The model to use
            **kwargs: Additional parameters like temperature, max_tokens, etc.
            
        Returns:
            A generator yielding content chunks as they become available
        """
        raise NotImplementedError("Subclasses must implement stream_chat_completion")
    
    @abstractmethod
    def call_tool(self, prompt: str, model: str, tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Use the model to call tools based on the prompt.
        
        Args:
            prompt: The user's message
            model: The model to use
            tools: List of tool definitions
            **kwargs: Additional parameters
            
        Returns:
            Dict containing the response and any tool calls
        """
        raise NotImplementedError("Subclasses must implement call_tool")


class ProviderFactory:
    """Factory for creating provider instances."""
    
    # Dictionary mapping provider names to their implementations
    _provider_classes = {}
    
    # Dictionary of initialized provider instances
    _instances = {}
    
    @classmethod
    def register_provider(cls, provider_name: str, provider_class) -> None:
        """
        Register a provider class with the factory.
        
        Args:
            provider_name: Name of the provider (e.g., 'anthropic', 'openai')
            provider_class: The provider class to register
        """
        cls._provider_classes[provider_name] = provider_class
        logger.info(f"Registered provider: {provider_name}")
    
    @classmethod
    def get_provider(cls, provider_name: str) -> Optional[BaseProvider]:
        """
        Get a provider instance by name. Initializes if not already initialized.
        
        Args:
            provider_name: Name of the provider to get
            
        Returns:
            Initialized provider instance or None if provider not registered
        """
        # Check if already initialized
        if provider_name in cls._instances:
            return cls._instances[provider_name]
        
        # Get the appropriate API key based on provider name
        api_key = cls._get_api_key(provider_name)
        
        # Try to initialize provider
        if provider_name in cls._provider_classes:
            try:
                # Initialize with API key
                cls._instances[provider_name] = cls._provider_classes[provider_name](api_key)
                
                logger.info(f"Initialized provider: {provider_name}")
                return cls._instances[provider_name]
            except Exception as e:
                logger.error(f"Failed to initialize provider {provider_name}: {str(e)}")
                return None
        else:
            logger.warning(f"Provider not registered: {provider_name}")
            return None
    
    @classmethod
    def _get_api_key(cls, provider_name: str) -> Optional[str]:
        """
        Get the API key for a provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            API key for the provider or None if not available
        """
        # In a real implementation, this would get API keys from environment variables
        # or a secure configuration system
        api_keys = {
            'anthropic': os.environ.get('ANTHROPIC_API_KEY'),
            'openai': os.environ.get('OPENAI_API_KEY'),
            'mistral': os.environ.get('MISTRAL_API_KEY'),
            'cohere': os.environ.get('COHERE_API_KEY'),
            'ollama': None  # Local providers don't need API keys
        }
        
        return api_keys.get(provider_name)
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, bool]:
        """
        Get all available providers and their availability status.
        
        Returns:
            Dictionary mapping provider names to their availability status
        """
        return {
            name: name in cls._provider_classes 
            for name in ['anthropic', 'openai', 'mistral', 'cohere', 'ollama']
        }


# Example implementation of an OpenAI provider
class OpenAIProvider(BaseProvider):
    """Example OpenAI provider implementation."""
    
    def __init__(self, api_key: str):
        """Initialize the OpenAI provider."""
        self.api_key = api_key
        self.client = None
        
        try:
            # In a real implementation, this would use the OpenAI client library
            # For this snippet, we'll just log the initialization
            logger.info("Initialized OpenAI provider with API key")
            self.client = True  # Placeholder for the actual client
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    
    def list_models(self, **kwargs) -> List[Dict[str, Any]]:
        """List available OpenAI models."""
        # In a real implementation, this would call the OpenAI API
        return [
            {"id": "gpt-4o", "name": "GPT-4o", "context_length": 128000},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "context_length": 128000},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "context_length": 16385}
        ]
    
    def chat_completion(self, prompt: str, model: str = "gpt-3.5-turbo", **kwargs) -> Dict[str, Any]:
        """Get a chat completion from OpenAI."""
        # In a real implementation, this would call the OpenAI API
        return {
            "id": "chatcmpl-123",
            "model": model,
            "content": f"This is a simulated response for: {prompt}",
            "finish_reason": "stop"
        }
    
    def stream_chat_completion(self, prompt: str, model: str = "gpt-3.5-turbo", **kwargs) -> Generator[str, None, None]:
        """Stream a chat completion from OpenAI."""
        # In a real implementation, this would stream from the OpenAI API
        words = f"This is a simulated streaming response for: {prompt}".split()
        for word in words:
            yield word + " "
    
    def call_tool(self, prompt: str, model: str, tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Call a tool using the OpenAI function calling capability."""
        # In a real implementation, this would use OpenAI's function calling
        return {
            "id": "chatcmpl-456",
            "model": model,
            "content": "I'll help you with that.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "San Francisco", "unit": "celsius"}'
                    }
                }
            ]
        }


# Register the example provider
ProviderFactory.register_provider('openai', OpenAIProvider) 