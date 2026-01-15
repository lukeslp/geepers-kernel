"""
Cohere Provider Tool Module

Exposes Cohere AI capabilities through the tool registry:
- Chat completion (Command A)
- Streaming completion
- Vision analysis (Command A Vision)

Author: Luke Steuber
"""

from typing import Dict, Any, List
from pathlib import Path

from .module_base import ToolModuleBase


class CohereTools(ToolModuleBase):
    """Cohere AI provider tools."""

    name = "cohere"
    display_name = "Cohere"
    description = "Cohere AI models with chat and vision capabilities"
    version = "1.0.0"

    def initialize(self):
        """Initialize Cohere tool schemas."""
        from llm_providers.cohere_provider import CohereProvider
        from llm_providers import Message

        self.Message = Message

        api_key = self.config.get('api_key')
        if not api_key:
            from config import ConfigManager
            config = ConfigManager()
            api_key = config.get_api_key('cohere')

        if not api_key:
            raise RuntimeError(
                "Cohere API key not configured. Set COHERE_API_KEY or provide via config."
            )

        self.provider = CohereProvider(api_key=api_key)

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "cohere_chat",
                    "description": "Generate chat completion using Cohere Command models",
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
                                "default": "command-a-03-2025"
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
                    "name": "cohere_vision",
                    "description": "Analyze image using Cohere Command Vision",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_path": {"type": "string"},
                            "prompt": {"type": "string"},
                            "model": {"type": "string", "default": "command-a-vision-07-2025"}
                        },
                        "required": ["image_path", "prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cohere_list_models",
                    "description": "List available Cohere models",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def cohere_chat(self, messages: List[Dict], model: str = "command-a-03-2025",
                    max_tokens: int = 1024, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate Cohere chat completion."""
        msg_objects = [self.Message(role=m["role"], content=m["content"]) for m in messages]
        response = self.provider.complete(
            msg_objects,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return self._format_completion_response(response)

    def cohere_vision(self, image_path: str, prompt: str,
                      model: str = "command-a-vision-07-2025") -> Dict[str, Any]:
        """Analyze image with Cohere vision."""
        if Path(image_path).exists():
            with open(image_path, 'rb') as f:
                image_data = f.read()
        else:
            image_data = image_path

        response = self.provider.analyze_image(image=image_data, prompt=prompt, model=model)
        analysis_dict = self._format_completion_response(response)
        analysis_dict["analysis"] = analysis_dict.pop("content", "")
        return analysis_dict

    def cohere_list_models(self) -> Dict[str, Any]:
        """List Cohere models."""
        models = self.provider.list_models()
        return {"models": models, "count": len(models), "provider": "cohere"}


if __name__ == '__main__':
    CohereTools.main()

