"""
HuggingFace Provider Tool Module

Exposes HuggingFace AI capabilities through the tool registry:
- Chat completion using Inference API
- Model listing

Author: Luke Steuber
"""

from typing import Dict, Any, List

from .module_base import ToolModuleBase


class HuggingFaceTools(ToolModuleBase):
    """HuggingFace AI provider tools."""

    name = "huggingface"
    display_name = "HuggingFace"
    description = "HuggingFace Inference API for open models"
    version = "1.0.0"

    def initialize(self):
        """Initialize HuggingFace tool schemas."""
        from llm_providers.huggingface_provider import HuggingFaceProvider
        from llm_providers import Message

        self.Message = Message

        api_key = self.config.get('api_key')
        if not api_key:
            from config import ConfigManager
            config = ConfigManager()
            api_key = config.get_api_key('huggingface')

        if not api_key:
            raise RuntimeError(
                "HuggingFace API key not configured. Set HF_API_KEY or provide via config."
            )

        self.provider = HuggingFaceProvider(api_key=api_key)

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "huggingface_chat",
                    "description": "Generate chat completion using HuggingFace models",
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
                                "description": "HuggingFace model name",
                                "default": "meta-llama/Llama-2-70b-chat-hf"
                            },
                            "max_tokens": {"type": "integer", "default": 1024},
                            "temperature": {"type": "number", "default": 0.7}
                        },
                        "required": ["messages"]
                    }
                }
            }
        ]

    def huggingface_chat(self, messages: List[Dict], model: str = "meta-llama/Llama-2-70b-chat-hf",
                         max_tokens: int = 1024, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate HuggingFace chat completion."""
        msg_objects = [self.Message(role=m["role"], content=m["content"]) for m in messages]
        response = self.provider.complete(
            msg_objects,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return self._format_completion_response(response)


if __name__ == '__main__':
    HuggingFaceTools.main()

