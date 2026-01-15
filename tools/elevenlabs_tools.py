"""
ElevenLabs TTS Tool Module

Exposes ElevenLabs text-to-speech capabilities through the tool registry.

Author: Luke Steuber
"""

from typing import Dict, Any

from .module_base import ToolModuleBase


class ElevenLabsTools(ToolModuleBase):
    """ElevenLabs text-to-speech tools."""

    name = "elevenlabs"
    display_name = "ElevenLabs TTS"
    description = "ElevenLabs text-to-speech generation"
    version = "1.0.0"

    def initialize(self):
        """Initialize ElevenLabs tool schemas."""
        from llm_providers.elevenlabs_provider import ElevenLabsProvider

        api_key = self.config.get('api_key')
        if not api_key:
            from config import ConfigManager
            config = ConfigManager()
            api_key = config.get_api_key('elevenlabs')

        if not api_key:
            raise RuntimeError(
                "ElevenLabs API key not configured. Set ELEVENLABS_API_KEY or provide via config."
            )

        self.provider = ElevenLabsProvider(api_key=api_key)

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "generate_speech",
                    "description": "Generate speech audio from text using ElevenLabs",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to convert to speech"
                            },
                            "voice_id": {
                                "type": "string",
                                "description": "Voice ID to use",
                                "default": "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
                            },
                            "model": {
                                "type": "string",
                                "description": "TTS model",
                                "default": "eleven_monolingual_v1"
                            }
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_voices",
                    "description": "List available ElevenLabs voices",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def generate_speech(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM",
                       model: str = "eleven_monolingual_v1") -> Dict[str, Any]:
        """Generate speech from text."""
        # This will need to be implemented in elevenlabs_provider
        try:
            audio_data = self.provider.generate_speech(text=text, voice_id=voice_id, model=model)
            return {
                "audio_data": audio_data,
                "format": "mp3",
                "text_length": len(text)
            }
        except AttributeError:
            return {"error": "ElevenLabs TTS not yet implemented in provider"}

    def list_voices(self) -> Dict[str, Any]:
        """List available voices."""
        try:
            voices = self.provider.list_voices()
            return {"voices": voices, "count": len(voices)}
        except AttributeError:
            return {"error": "Voice listing not yet implemented in provider"}


if __name__ == '__main__':
    ElevenLabsTools.main()

