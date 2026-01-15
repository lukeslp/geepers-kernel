"""
Perplexity Provider Tool Module

Exposes Perplexity AI capabilities through the tool registry:
- Chat completion with web search and citations
- Streaming completion

Author: Luke Steuber
"""

from typing import Dict, Any

from .module_base import ToolModuleBase


class PerplexityTools(ToolModuleBase):
    """Perplexity AI provider tools."""

    name = "perplexity"
    display_name = "Perplexity"
    description = "Perplexity AI models with web search and citations"
    version = "1.0.0"

    def initialize(self):
        """Initialize Perplexity tool schemas."""
        from llm_providers.perplexity_provider import PerplexityProvider
        from llm_providers import Message

        self.Message = Message

        api_key = self.config.get('api_key')
        if not api_key:
            from config import ConfigManager
            config = ConfigManager()
            api_key = config.get_api_key('perplexity')

        if not api_key:
            raise RuntimeError(
                "Perplexity API key not configured. Set PERPLEXITY_API_KEY or provide via config."
            )

        self.provider = PerplexityProvider(api_key=api_key)

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "perplexity_search",
                    "description": "Search and answer using Perplexity (includes web search and citations)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query or question"
                            },
                            "model": {
                                "type": "string",
                                "description": "Perplexity model (sonar-pro, sonar-reasoning-pro)",
                                "default": "sonar-pro"
                            },
                            "max_tokens": {"type": "integer", "default": 1024}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "perplexity_list_models",
                    "description": "List available Perplexity models",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def perplexity_search(self, query: str, model: str = "sonar-pro", max_tokens: int = 1024) -> Dict[str, Any]:
        """Search with Perplexity (includes citations)."""
        messages = [self.Message(role="user", content=query)]
        response = self.provider.complete(messages, model=model, max_tokens=max_tokens)
        result = self._format_completion_response(response)
        result["answer"] = result.pop("content", "")
        result.setdefault("metadata", {})
        result["metadata"]["has_citations"] = True
        return result

    def perplexity_list_models(self) -> Dict[str, Any]:
        """List Perplexity models."""
        models = self.provider.list_models()
        return {"models": models, "count": len(models), "provider": "perplexity"}


if __name__ == '__main__':
    PerplexityTools.main()

