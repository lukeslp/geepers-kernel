"""
Vision Analysis Tool Module

Multi-provider vision analysis tool using the best available provider.

Author: Luke Steuber
"""

from typing import Dict, Any
from pathlib import Path

from .module_base import ToolModuleBase


class VisionTools(ToolModuleBase):
    """Multi-provider vision analysis tools."""

    name = "vision"
    display_name = "Vision Analysis"
    description = "Analyze images using multiple AI providers"
    version = "1.0.0"

    def initialize(self):
        """Initialize vision tool schemas."""
        from config import ConfigManager

        self.config_mgr = ConfigManager()
        self.available_providers = []

        # Check which vision providers are available
        if self.config_mgr.has_api_key('openai'):
            self.available_providers.append('openai')
        if self.config_mgr.has_api_key('anthropic'):
            self.available_providers.append('anthropic')
        if self.config_mgr.has_api_key('xai'):
            self.available_providers.append('xai')
        if self.config_mgr.has_api_key('gemini'):
            self.available_providers.append('gemini')
        if self.config_mgr.has_api_key('cohere'):
            self.available_providers.append('cohere')

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "analyze_image",
                    "description": "Analyze image using best available vision provider",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_path": {
                                "type": "string",
                                "description": "Path to image file or base64 string"
                            },
                            "prompt": {
                                "type": "string",
                                "description": "What to analyze or ask about the image"
                            },
                            "provider": {
                                "type": "string",
                                "description": "Specific provider to use",
                                "enum": ["auto", "openai", "anthropic", "xai", "gemini", "cohere"],
                                "default": "auto"
                            }
                        },
                        "required": ["image_path", "prompt"]
                    }
                }
            }
        ]

    def analyze_image(self, image_path: str, prompt: str, provider: str = "auto") -> Dict[str, Any]:
        """
        Analyze image using vision AI.

        Args:
            image_path: Path to image or base64 string
            prompt: Question or analysis request
            provider: Which provider to use (auto selects best available)

        Returns:
            Dict with analysis and metadata
        """
        # Auto-select provider
        if provider == "auto":
            if not self.available_providers:
                return {"error": "No vision providers available (check API keys)"}
            provider = self.available_providers[0]  # Use first available

        # Validate provider
        if provider not in self.available_providers:
            return {"error": f"Provider {provider} not available. Available: {self.available_providers}"}

        # Load image
        if Path(image_path).exists():
            with open(image_path, 'rb') as f:
                image_data = f.read()
        else:
            # Assume base64
            image_data = image_path

        # Get provider instance
        from llm_providers.factory import ProviderFactory

        try:
            provider_instance = ProviderFactory.get_provider(
                provider,
                api_key=self.config_mgr.get_api_key(provider)
            )

            # Analyze image
            response = provider_instance.analyze_image(image=image_data, prompt=prompt)

            result = self._format_completion_response(response)
            result["analysis"] = result.pop("content", "")
            result["provider"] = provider
            return result
        except Exception as e:
            return {"error": f"Vision analysis failed: {str(e)}"}


if __name__ == '__main__':
    VisionTools.main()

