"""
Mistral Provider Tool Module

Exposes Mistral AI capabilities through the tool registry:
- Chat completion (Mistral Large, Medium)
- Streaming completion

Author: Luke Steuber
"""

from typing import Dict, Any, List

from .module_base import ToolModuleBase


class MistralTools(ToolModuleBase):
    """Mistral AI provider tools."""

    name = "mistral"
    display_name = "Mistral AI"
    description = "Mistral AI models for chat completion"
    version = "1.0.0"

    def initialize(self):
        """Initialize Mistral tool schemas."""
        from llm_providers.mistral_provider import MistralProvider
        from llm_providers import Message

        self.Message = Message

        api_key = self.config.get('api_key')
        if not api_key:
            from config import ConfigManager
            config = ConfigManager()
            api_key = config.get_api_key('mistral')

        if not api_key:
            raise RuntimeError(
                "Mistral API key not configured. Set MISTRAL_API_KEY or provide via config."
            )

        self.provider = MistralProvider(api_key=api_key)

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "mistral_chat",
                    "description": "Generate chat completion using Mistral AI",
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
                                "description": "Mistral model",
                                "default": "mistral-large-latest"
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
                    "name": "mistral_list_models",
                    "description": "List available Mistral models",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def mistral_chat(self, messages: List[Dict], model: str = "mistral-large-latest",
                     max_tokens: int = 1024, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate Mistral chat completion."""
        msg_objects = [self.Message(role=m["role"], content=m["content"]) for m in messages]
        response = self.provider.complete(
            msg_objects,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return self._format_completion_response(response)

    def mistral_list_models(self) -> Dict[str, Any]:
        """List Mistral models."""
        models = self.provider.list_models()
        return {"models": models, "count": len(models), "provider": "mistral"}


if __name__ == '__main__':
    MistralTools.main()

