"""
Google Gemini Provider Tool Module

Exposes Google Gemini capabilities through the tool registry:
- Chat completion (Gemini 2.5 Pro/Flash)
- Streaming completion
- Vision analysis
- Image generation (Imagen)

Author: Luke Steuber
"""

from typing import Dict, Any, List
from pathlib import Path

from .module_base import ToolModuleBase


class GeminiTools(ToolModuleBase):
    """Google Gemini provider tools."""

    name = "gemini"
    display_name = "Google Gemini"
    description = "Google Gemini models with chat, vision, and image generation"
    version = "1.0.0"

    def initialize(self):
        """Initialize Gemini tool schemas."""
        from llm_providers.gemini_provider import GeminiProvider
        from llm_providers import Message

        self.Message = Message

        api_key = self.config.get('api_key')
        if not api_key:
            from config import ConfigManager
            config = ConfigManager()
            api_key = config.get_api_key('gemini')

        if not api_key:
            raise RuntimeError(
                "Gemini API key not configured. Set GEMINI_API_KEY or provide via config."
            )

        self.provider = GeminiProvider(api_key=api_key)

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "gemini_chat",
                    "description": "Generate chat completion using Google Gemini",
                    "parameters": {
                        "type": "object",
                        "properties": {
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
                            "model": {
                                "type": "string",
                                "description": "Gemini model",
                                "default": "gemini-2.5-pro-preview-03-25"
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
                    "name": "gemini_vision",
                    "description": "Analyze image using Gemini Pro Vision",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_path": {"type": "string"},
                            "prompt": {"type": "string"},
                            "model": {"type": "string", "default": "gemini-2.5-pro-preview-03-25"}
                        },
                        "required": ["image_path", "prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gemini_list_models",
                    "description": "List available Gemini models",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def gemini_chat(self, messages: List[Dict], model: str = "gemini-2.5-pro-preview-03-25",
                    max_tokens: int = 1024, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate Gemini chat completion."""
        msg_objects = [self.Message(role=m["role"], content=m["content"]) for m in messages]
        response = self.provider.complete(
            msg_objects,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return self._format_completion_response(response)

    def gemini_vision(self, image_path: str, prompt: str,
                      model: str = "gemini-2.5-pro-preview-03-25") -> Dict[str, Any]:
        """Analyze image with Gemini vision."""
        if Path(image_path).exists():
            with open(image_path, 'rb') as f:
                image_data = f.read()
        else:
            image_data = image_path

        response = self.provider.analyze_image(image=image_data, prompt=prompt, model=model)
        analysis_dict = self._format_completion_response(response)
        analysis_dict["analysis"] = analysis_dict.pop("content", "")
        return analysis_dict

    def gemini_list_models(self) -> Dict[str, Any]:
        """List Gemini models."""
        models = self.provider.list_models()
        return {"models": models, "count": len(models), "provider": "gemini"}


if __name__ == '__main__':
    GeminiTools.main()

