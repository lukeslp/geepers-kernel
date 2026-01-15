"""
OpenAI Provider Tool Module

Exposes OpenAI (GPT) capabilities through the tool registry:
- Chat completion (GPT-4, GPT-4o, GPT-3.5)
- Streaming completion
- Vision analysis (GPT-4o)
- Image generation (DALL-E)
- Model listing

Author: Luke Steuber
"""

from typing import Dict, Any, List
from pathlib import Path

from .module_base import ToolModuleBase


class OpenAITools(ToolModuleBase):
    """OpenAI (GPT) provider tools."""

    # Module metadata
    name = "openai"
    display_name = "OpenAI (GPT)"
    description = "OpenAI GPT models with chat, vision, and DALL-E image generation"
    version = "1.0.0"

    def initialize(self):
        """Initialize OpenAI tool schemas."""
        # Import here to avoid circular dependencies
        from llm_providers.openai_provider import OpenAIProvider
        from llm_providers import Message

        self.Message = Message

        # Initialize provider
        api_key = self.config.get('api_key')
        if not api_key:
            from config import ConfigManager
            config = ConfigManager()
            api_key = config.get_api_key('openai')

        if not api_key:
            raise RuntimeError(
                "OpenAI API key not configured. Set OPENAI_API_KEY or provide via config."
            )

        self.provider = OpenAIProvider(api_key=api_key)

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "openai_chat",
                    "description": "Generate chat completion using OpenAI GPT models",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "messages": {
                                "type": "array",
                                "description": "List of message objects with role and content",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                                        "content": {"type": "string"}
                                    },
                                    "required": ["role", "content"]
                                }
                            },
                            "model": {
                                "type": "string",
                                "description": "Model to use (e.g., gpt-4, gpt-4o-mini)",
                                "default": "gpt-4"
                            },
                            "max_tokens": {
                                "type": "integer",
                                "description": "Maximum tokens to generate",
                                "default": 1024
                            },
                            "temperature": {
                                "type": "number",
                                "description": "Sampling temperature (0.0-2.0)",
                                "default": 0.7
                            }
                        },
                        "required": ["messages"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "openai_vision",
                    "description": "Analyze image using GPT-4o vision capabilities",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_path": {
                                "type": "string",
                                "description": "Path to image file or base64-encoded image"
                            },
                            "prompt": {
                                "type": "string",
                                "description": "What to analyze in the image"
                            },
                            "model": {
                                "type": "string",
                                "description": "Vision model to use",
                                "default": "gpt-4o"
                            }
                        },
                        "required": ["image_path", "prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "openai_generate_image",
                    "description": "Generate image using DALL-E",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Description of image to generate"
                            },
                            "size": {
                                "type": "string",
                                "description": "Image size",
                                "enum": ["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"],
                                "default": "1024x1024"
                            },
                            "quality": {
                                "type": "string",
                                "description": "Image quality",
                                "enum": ["standard", "hd"],
                                "default": "standard"
                            },
                            "model": {
                                "type": "string",
                                "description": "DALL-E model",
                                "enum": ["dall-e-2", "dall-e-3"],
                                "default": "dall-e-3"
                            }
                        },
                        "required": ["prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "openai_list_models",
                    "description": "List available OpenAI models",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]

    def openai_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate chat completion using OpenAI GPT.

        Args:
            messages: List of message dicts with role and content
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Dict with response content, model, and usage stats
        """
        # Convert dict messages to Message objects
        msg_objects = [self.Message(role=m["role"], content=m["content"]) for m in messages]

        # Generate completion
        response = self.provider.complete(
            messages=msg_objects,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )

        return self._format_completion_response(response)

    def openai_vision(
        self,
        image_path: str,
        prompt: str,
        model: str = "gpt-4o"
    ) -> Dict[str, Any]:
        """
        Analyze image using GPT-4o vision.

        Args:
            image_path: Path to image file or base64 string
            prompt: What to analyze
            model: Vision model to use

        Returns:
            Dict with analysis, model, and usage stats
        """
        # Load image
        if Path(image_path).exists():
            with open(image_path, 'rb') as f:
                image_data = f.read()
        else:
            # Assume it's base64
            image_data = image_path

        # Analyze image
        response = self.provider.analyze_image(
            image=image_data,
            prompt=prompt,
            model=model
        )

        analysis_dict = self._format_completion_response(response)
        analysis_dict["analysis"] = analysis_dict.pop("content", "")
        return analysis_dict

    def openai_generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        model: str = "dall-e-3"
    ) -> Dict[str, Any]:
        """
        Generate image using DALL-E.

        Args:
            prompt: Description of image
            size: Image dimensions
            quality: standard or hd
            model: DALL-E model version

        Returns:
            Dict with base64 image data and metadata
        """
        response = self.provider.generate_image(
            prompt=prompt,
            size=size,
            quality=quality,
            model=model
        )

        return self._format_image_response(response)

    def openai_list_models(self) -> Dict[str, Any]:
        """
        List available OpenAI models.

        Returns:
            Dict with list of model names
        """
        models = self.provider.list_models()

        return {
            "models": models,
            "count": len(models),
            "provider": "openai"
        }


# CLI entry point
if __name__ == '__main__':
    OpenAITools.main()

