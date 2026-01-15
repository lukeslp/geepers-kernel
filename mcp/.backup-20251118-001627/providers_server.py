"""
Providers MCP Server

Exposes shared.llm_providers capabilities through MCP protocol.

Tools provided:
- create_provider: Instantiate a provider
- list_provider_models: Get available models
- chat_completion: Generate chat response
- stream_chat: Stream chat response
- generate_image: Generate image (DALL-E, Aurora)
- analyze_image: Analyze image with vision

Resources provided:
- provider://{name}/info: Provider metadata
- provider://{name}/models: Available models list
"""

import json
import logging
from typing import Dict, List, Optional, Any
import asyncio

# Import from shared library
import sys
sys.path.insert(0, '/home/coolhand/shared')
from llm_providers import Message, CompletionResponse
from llm_providers.factory import ProviderFactory
from config import ConfigManager

logger = logging.getLogger(__name__)


class ProvidersServer:
    """
    MCP server for LLM provider capabilities.

    Exposes shared.llm_providers.ProviderFactory through MCP protocol.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize providers MCP server.

        Args:
            config_manager: ConfigManager instance (creates new one if None)
        """
        self.config = config_manager or ConfigManager(app_name='mcp_providers')
        self.providers_cache = {}  # provider_name -> provider_instance

    def get_provider(self, provider_name: str, model: Optional[str] = None):
        """
        Get or create provider instance.

        Args:
            provider_name: Name of the provider (anthropic, openai, etc.)
            model: Optional model name

        Returns:
            Provider instance

        Raises:
            ValueError: If provider not configured or invalid
        """
        cache_key = f"{provider_name}:{model or 'default'}"

        if cache_key in self.providers_cache:
            return self.providers_cache[cache_key]

        api_key = self.config.get_api_key(provider_name)
        if not api_key:
            raise ValueError(f"No API key configured for provider: {provider_name}")

        try:
            provider = ProviderFactory.create_provider(
                provider_name=provider_name,
                api_key=api_key,
                model=model
            )
            self.providers_cache[cache_key] = provider
            return provider

        except Exception as e:
            logger.error(f"Failed to create provider {provider_name}: {e}")
            raise

    # -------------------------------------------------------------------------
    # MCP Tools
    # -------------------------------------------------------------------------

    def tool_create_provider(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: create_provider

        Creates and caches a provider instance.

        Arguments:
            provider_name (str): Name of the provider
            model (str, optional): Model name

        Returns:
            {success: bool, provider: str, model: str, models_available: int}
        """
        try:
            provider_name = arguments.get('provider_name')
            model = arguments.get('model')

            if not provider_name:
                return {
                    "success": False,
                    "error": "Missing required argument: provider_name"
                }

            provider = self.get_provider(provider_name, model)
            models = provider.list_models()

            return {
                "success": True,
                "provider": provider_name,
                "model": model or "default",
                "models_available": len(models),
                "supports_vision": hasattr(provider, 'analyze_image'),
                "supports_image_gen": hasattr(provider, 'generate_image')
            }

        except Exception as e:
            logger.exception(f"Error in create_provider: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_list_provider_models(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: list_provider_models

        Lists available models for a provider.

        Arguments:
            provider_name (str): Name of the provider

        Returns:
            {success: bool, provider: str, models: List[str]}
        """
        try:
            provider_name = arguments.get('provider_name')
            if not provider_name:
                return {
                    "success": False,
                    "error": "Missing required argument: provider_name"
                }

            provider = self.get_provider(provider_name)
            models = provider.list_models()

            return {
                "success": True,
                "provider": provider_name,
                "models": models
            }

        except Exception as e:
            logger.exception(f"Error in list_provider_models: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_chat_completion(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: chat_completion

        Generate chat completion using a provider.

        Arguments:
            provider_name (str): Name of the provider
            messages (List[Dict]): Conversation messages
            model (str, optional): Model name
            max_tokens (int, optional): Max tokens
            temperature (float, optional): Sampling temperature

        Returns:
            {success: bool, content: str, model: str, usage: Dict}
        """
        try:
            provider_name = arguments.get('provider_name')
            messages_data = arguments.get('messages', [])

            if not provider_name or not messages_data:
                return {
                    "success": False,
                    "error": "Missing required arguments: provider_name and messages"
                }

            # Parse messages
            messages = [
                Message(role=msg.get('role', 'user'), content=msg.get('content', ''))
                for msg in messages_data
            ]

            # Get provider
            provider = self.get_provider(provider_name, arguments.get('model'))

            # Build kwargs
            kwargs = {}
            if 'max_tokens' in arguments:
                kwargs['max_tokens'] = arguments['max_tokens']
            if 'temperature' in arguments:
                kwargs['temperature'] = arguments['temperature']

            # Generate completion
            response = provider.complete(messages, **kwargs)

            return {
                "success": True,
                "content": response.content,
                "model": response.model,
                "usage": response.usage
            }

        except Exception as e:
            logger.exception(f"Error in chat_completion: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_generate_image(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: generate_image

        Generate image using DALL-E or Aurora.

        Arguments:
            provider_name (str): Name of the provider (openai or xai)
            prompt (str): Image description
            model (str, optional): Model name
            size (str, optional): Image size

        Returns:
            {success: bool, image_data: str (base64), model: str}
        """
        try:
            provider_name = arguments.get('provider_name')
            prompt = arguments.get('prompt')

            if not provider_name or not prompt:
                return {
                    "success": False,
                    "error": "Missing required arguments: provider_name and prompt"
                }

            provider = self.get_provider(provider_name, arguments.get('model'))

            # Build kwargs
            kwargs = {}
            if 'size' in arguments:
                kwargs['size'] = arguments['size']

            try:
                response = provider.generate_image(prompt, **kwargs)

                return {
                    "success": True,
                    "image_data": response.image_data,
                    "model": response.model,
                    "revised_prompt": response.revised_prompt
                }

            except NotImplementedError:
                return {
                    "success": False,
                    "error": f"Provider {provider_name} does not support image generation"
                }

        except Exception as e:
            logger.exception(f"Error in generate_image: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_analyze_image(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: analyze_image

        Analyze image using vision capabilities.

        Arguments:
            provider_name (str): Name of the provider
            image_data (str): Base64-encoded image
            prompt (str): Question about the image
            model (str, optional): Model name

        Returns:
            {success: bool, content: str, model: str}
        """
        try:
            provider_name = arguments.get('provider_name')
            image_data = arguments.get('image_data')
            prompt = arguments.get('prompt', "Describe this image")

            if not provider_name or not image_data:
                return {
                    "success": False,
                    "error": "Missing required arguments: provider_name and image_data"
                }

            provider = self.get_provider(provider_name, arguments.get('model'))

            try:
                response = provider.analyze_image(image_data, prompt)

                return {
                    "success": True,
                    "content": response.content,
                    "model": response.model,
                    "usage": response.usage
                }

            except NotImplementedError:
                return {
                    "success": False,
                    "error": f"Provider {provider_name} does not support vision"
                }

        except Exception as e:
            logger.exception(f"Error in analyze_image: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Resources
    # -------------------------------------------------------------------------

    def resource_provider_info(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: provider://{name}/info

        Returns metadata about a provider.

        Args:
            uri: Resource URI (e.g., "provider://anthropic/info")

        Returns:
            Provider metadata
        """
        try:
            # Parse URI: provider://{name}/info
            parts = uri.replace('provider://', '').split('/')
            provider_name = parts[0]

            provider = self.get_provider(provider_name)
            models = provider.list_models()

            return {
                "uri": uri,
                "provider": provider_name,
                "models_count": len(models),
                "supports_vision": hasattr(provider, 'analyze_image'),
                "supports_image_gen": hasattr(provider, 'generate_image'),
                "supports_streaming": hasattr(provider, 'stream_complete'),
                "configured": True
            }

        except Exception as e:
            logger.exception(f"Error in resource_provider_info: {e}")
            return {
                "uri": uri,
                "error": str(e),
                "configured": False
            }

    def resource_provider_models(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: provider://{name}/models

        Returns list of available models for a provider.

        Args:
            uri: Resource URI (e.g., "provider://anthropic/models")

        Returns:
            Models list
        """
        try:
            # Parse URI: provider://{name}/models
            parts = uri.replace('provider://', '').split('/')
            provider_name = parts[0]

            provider = self.get_provider(provider_name)
            models = provider.list_models()

            return {
                "uri": uri,
                "provider": provider_name,
                "models": models
            }

        except Exception as e:
            logger.exception(f"Error in resource_provider_models: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Server Interface
    # -------------------------------------------------------------------------

    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP tools manifest.

        Returns:
            List of tool definitions
        """
        return [
            {
                "name": "create_provider",
                "description": "Create and cache a provider instance",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider_name": {
                            "type": "string",
                            "description": "Provider name (anthropic, openai, xai, etc.)"
                        },
                        "model": {
                            "type": "string",
                            "description": "Model name (optional)"
                        }
                    },
                    "required": ["provider_name"]
                }
            },
            {
                "name": "list_provider_models",
                "description": "List available models for a provider",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider_name": {
                            "type": "string",
                            "description": "Provider name"
                        }
                    },
                    "required": ["provider_name"]
                }
            },
            {
                "name": "chat_completion",
                "description": "Generate chat completion",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider_name": {"type": "string"},
                        "messages": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "role": {"type": "string"},
                                    "content": {"type": "string"}
                                }
                            }
                        },
                        "model": {"type": "string"},
                        "max_tokens": {"type": "integer"},
                        "temperature": {"type": "number"}
                    },
                    "required": ["provider_name", "messages"]
                }
            },
            {
                "name": "generate_image",
                "description": "Generate image using DALL-E or Aurora",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider_name": {"type": "string"},
                        "prompt": {"type": "string"},
                        "model": {"type": "string"},
                        "size": {"type": "string"}
                    },
                    "required": ["provider_name", "prompt"]
                }
            },
            {
                "name": "analyze_image",
                "description": "Analyze image with vision capabilities",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider_name": {"type": "string"},
                        "image_data": {"type": "string", "description": "Base64-encoded image"},
                        "prompt": {"type": "string"},
                        "model": {"type": "string"}
                    },
                    "required": ["provider_name", "image_data"]
                }
            }
        ]

    def get_resources_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP resources manifest.

        Returns:
            List of resource templates
        """
        available_providers = self.config.list_available_providers()

        resources = []
        for provider_name in available_providers:
            resources.extend([
                {
                    "uri": f"provider://{provider_name}/info",
                    "name": f"{provider_name} Info",
                    "description": f"Metadata about {provider_name} provider",
                    "mimeType": "application/json"
                },
                {
                    "uri": f"provider://{provider_name}/models",
                    "name": f"{provider_name} Models",
                    "description": f"Available models for {provider_name}",
                    "mimeType": "application/json"
                }
            ])

        return resources
