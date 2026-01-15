"""
Image Generation Tool Module

Multi-provider image generation tool:
- OpenAI DALL-E
- xAI Aurora
- (Future: Stable Diffusion, Midjourney)

Author: Luke Steuber
"""

from typing import Dict, Any

from .module_base import ToolModuleBase


class ImageGenerationTools(ToolModuleBase):
    """Multi-provider image generation tools."""

    name = "image_gen"
    display_name = "Image Generation"
    description = "Generate images using DALL-E, Aurora, and other AI models"
    version = "1.0.0"

    def initialize(self):
        """Initialize image generation tool schemas."""
        from config import ConfigManager

        self.config_mgr = ConfigManager()
        self.available_providers = []

        # Check which image gen providers are available
        if self.config_mgr.has_api_key('openai'):
            self.available_providers.append('openai')  # DALL-E
        if self.config_mgr.has_api_key('xai'):
            self.available_providers.append('xai')  # Aurora

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "Generate image from text prompt using AI",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Description of image to generate"
                            },
                            "provider": {
                                "type": "string",
                                "description": "Image generation provider",
                                "enum": ["auto", "openai", "xai"],
                                "default": "auto"
                            },
                            "size": {
                                "type": "string",
                                "description": "Image size",
                                "default": "1024x1024"
                            },
                            "quality": {
                                "type": "string",
                                "description": "Image quality (for DALL-E)",
                                "enum": ["standard", "hd"],
                                "default": "standard"
                            }
                        },
                        "required": ["prompt"]
                    }
                }
            }
        ]

    def generate_image(self, prompt: str, provider: str = "auto",
                      size: str = "1024x1024", quality: str = "standard") -> Dict[str, Any]:
        """
        Generate image from text prompt.

        Args:
            prompt: Description of image
            provider: Which provider to use
            size: Image dimensions
            quality: Image quality

        Returns:
            Dict with base64 image data and metadata
        """
        # Auto-select provider
        if provider == "auto":
            if not self.available_providers:
                return {"error": "No image generation providers available (check API keys)"}
            provider = self.available_providers[0]  # Prefer OpenAI

        # Validate provider
        if provider not in self.available_providers:
            return {"error": f"Provider {provider} not available. Available: {self.available_providers}"}

        # Get provider instance
        from llm_providers.factory import ProviderFactory

        try:
            provider_instance = ProviderFactory.get_provider(
                provider,
                api_key=self.config_mgr.get_api_key(provider)
            )

            # Generate image
            if provider == "openai":
                response = provider_instance.generate_image(
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    model="dall-e-3"
                )
            else:  # xai/aurora
                response = provider_instance.generate_image(prompt=prompt, size=size)

            result = self._format_image_response(response)
            result["provider"] = provider
            return result
        except Exception as e:
            return {"error": f"Image generation failed: {str(e)}"}


if __name__ == '__main__':
    ImageGenerationTools.main()

