"""
xAI (Grok) Provider Tool Module

Exposes xAI Grok capabilities through the tool registry:
- Chat completion (Grok-4, Grok-3)
- Streaming completion
- Vision analysis (Grok-2-vision)
- Image generation (Aurora)

Author: Luke Steuber
"""

from typing import Dict, Any, List
from pathlib import Path

from .module_base import ToolModuleBase


class XAITools(ToolModuleBase):
    """xAI Grok provider tools."""

    name = "xai"
    display_name = "xAI (Grok)"
    description = "xAI Grok models with chat, vision, and Aurora image generation"
    version = "1.0.0"

    def initialize(self):
        """Initialize xAI tool schemas."""
        from llm_providers.xai_provider import XAIProvider
        from llm_providers import Message

        self.Message = Message

        api_key = self.config.get('api_key')
        if not api_key:
            from config import ConfigManager
            config = ConfigManager()
            api_key = config.get_api_key('xai')

        if not api_key:
            raise RuntimeError(
                "xAI API key not configured. Set XAI_API_KEY or provide via config."
            )

        self.provider = XAIProvider(api_key=api_key)

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "grok_chat",
                    "description": "Generate chat completion using xAI Grok",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "messages": {
                                "type": "array",
                                "description": "List of message objects",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "role": {"type": "string"},
                                        "content": {"type": "string"}
                                    }
                                }
                            },
                            "model": {
                                "type": "string",
                                "description": "Grok model (grok-4, grok-3, grok-2-vision-1212)",
                                "default": "grok-4"
                            },
                            "max_tokens": {"type": "integer", "default": 1024},
                            "temperature": {"type": "number", "default": 0.7}
                        },
                        "required": ["messages"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "grok_vision",
                    "description": "Analyze image using Grok-2-vision",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_path": {"type": "string"},
                            "prompt": {"type": "string"},
                            "model": {"type": "string", "default": "grok-2-vision-1212"}
                        },
                        "required": ["image_path", "prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "grok_generate_image",
                    "description": "Generate image using xAI Aurora",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"},
                            "size": {"type": "string", "default": "1024x1024"}
                        },
                        "required": ["prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "grok_list_models",
                    "description": "List available Grok models",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def grok_chat(self, messages: List[Dict], model: str = "grok-4",
                  max_tokens: int = 1024, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate Grok chat completion."""
        msg_objects = [self.Message(role=m["role"], content=m["content"]) for m in messages]
        response = self.provider.complete(
            msg_objects,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return self._format_completion_response(response)

    def grok_vision(self, image_path: str, prompt: str, model: str = "grok-2-vision-1212") -> Dict[str, Any]:
        """Analyze image with Grok vision."""
        if Path(image_path).exists():
            with open(image_path, 'rb') as f:
                image_data = f.read()
        else:
            image_data = image_path

        response = self.provider.analyze_image(image=image_data, prompt=prompt, model=model)
        analysis_dict = self._format_completion_response(response)
        analysis_dict["analysis"] = analysis_dict.pop("content", "")
        return analysis_dict

    def grok_generate_image(self, prompt: str, size: str = "1024x1024") -> Dict[str, Any]:
        """Generate image with Aurora."""
        response = self.provider.generate_image(prompt=prompt, size=size)
        return self._format_image_response(response)

    def grok_list_models(self) -> Dict[str, Any]:
        """List Grok models."""
        models = self.provider.list_models()
        return {"models": models, "count": len(models), "provider": "xai"}


if __name__ == '__main__':
    XAITools.main()

