"""
Groq Provider Tool Module

Exposes Groq AI capabilities through the tool registry:
- Chat completion (fast inference)
- Streaming completion

Author: Luke Steuber
"""

from typing import Dict, Any, List

from .module_base import ToolModuleBase


class GroqTools(ToolModuleBase):
    """Groq AI provider tools."""

    name = "groq"
    display_name = "Groq"
    description = "Groq AI fast inference models"
    version = "1.0.0"

    def initialize(self):
        """Initialize Groq tool schemas."""
        from llm_providers.groq_provider import GroqProvider
        from llm_providers import Message

        self.Message = Message

        api_key = self.config.get('api_key')
        if not api_key:
            from config import ConfigManager
            config = ConfigManager()
            api_key = config.get_api_key('groq')

        if not api_key:
            raise RuntimeError(
                "Groq API key not configured. Set GROQ_API_KEY or provide via config."
            )

        self.provider = GroqProvider(api_key=api_key)

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "groq_chat",
                    "description": "Fast chat completion using Groq",
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
                            "model": {"type": "string", "default": "mixtral-8x7b-32768"},
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
                    "name": "groq_list_models",
                    "description": "List available Groq models",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def groq_chat(self, messages: List[Dict], model: str = "mixtral-8x7b-32768",
                  max_tokens: int = 1024, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate Groq chat completion."""
        msg_objects = [self.Message(role=m["role"], content=m["content"]) for m in messages]
        response = self.provider.complete(
            msg_objects,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return self._format_completion_response(response)

    def groq_list_models(self) -> Dict[str, Any]:
        """List Groq models."""
        models = self.provider.list_models()
        return {"models": models, "count": len(models), "provider": "groq"}


if __name__ == '__main__':
    GroqTools.main()

