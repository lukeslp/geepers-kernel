"""
Anthropic (Claude) Provider Tool Module

Exposes Anthropic Claude capabilities through the tool registry:
- Chat completion (Claude Sonnet, Opus, Haiku)
- Streaming completion
- Vision analysis

Author: Luke Steuber
"""

from typing import Dict, Any, List
from pathlib import Path

from .module_base import ToolModuleBase


class AnthropicTools(ToolModuleBase):
    """Anthropic Claude provider tools."""

    name = "anthropic"
    display_name = "Anthropic (Claude)"
    description = "Anthropic Claude models with chat and vision capabilities"
    version = "1.0.0"

    def initialize(self):
        """Initialize Anthropic tool schemas."""
        from llm_providers.anthropic_provider import AnthropicProvider
        from llm_providers import Message

        self.Message = Message

        # Initialize provider
        api_key = self.config.get('api_key')
        if not api_key:
            from config import ConfigManager
            config = ConfigManager()
            api_key = config.get_api_key('anthropic')

        if not api_key:
            raise RuntimeError(
                "Anthropic API key not configured. Set ANTHROPIC_API_KEY or provide via config."
            )

        self.provider = AnthropicProvider(api_key=api_key)

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "anthropic_chat",
                    "description": "Generate chat completion using Anthropic Claude",
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
                                "description": "Claude model (sonnet, opus, haiku)",
                                "default": "claude-sonnet-4-5-20250929"
                            },
                            "max_tokens": {"type": "integer", "default": 4096},
                            "temperature": {"type": "number", "default": 0.7}
                        },
                        "required": ["messages"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "anthropic_vision",
                    "description": "Analyze image using Claude vision",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_path": {"type": "string", "description": "Path to image file"},
                            "prompt": {"type": "string", "description": "What to analyze"},
                            "model": {"type": "string", "default": "claude-sonnet-4-5-20250929"}
                        },
                        "required": ["image_path", "prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "anthropic_list_models",
                    "description": "List available Anthropic models",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def anthropic_chat(self, messages: List[Dict], model: str = "claude-sonnet-4-5-20250929",
                       max_tokens: int = 4096, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate Claude chat completion."""
        msg_objects = [self.Message(role=m["role"], content=m["content"]) for m in messages]
        response = self.provider.complete(
            msg_objects,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return self._format_completion_response(response)

    def anthropic_vision(self, image_path: str, prompt: str,
                        model: str = "claude-sonnet-4-5-20250929") -> Dict[str, Any]:
        """Analyze image with Claude vision."""
        if Path(image_path).exists():
            with open(image_path, 'rb') as f:
                image_data = f.read()
        else:
            image_data = image_path

        response = self.provider.analyze_image(image=image_data, prompt=prompt, model=model)
        analysis_dict = self._format_completion_response(response)
        analysis_dict["analysis"] = analysis_dict.pop("content", "")
        return analysis_dict

    def anthropic_list_models(self) -> Dict[str, Any]:
        """List Claude models."""
        models = self.provider.list_models()
        return {"models": models, "count": len(models), "provider": "anthropic"}


if __name__ == '__main__':
    AnthropicTools.main()

