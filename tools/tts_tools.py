"""
Text-to-Speech Tool Module

Multi-provider TTS tool:
- Google TTS (gTTS) - Free, no API key
- ElevenLabs - High quality, requires API key

Author: Luke Steuber
"""

from typing import Dict, Any
import os

from .module_base import ToolModuleBase


class TTSTools(ToolModuleBase):
    """Text-to-speech tools."""

    name = "tts"
    display_name = "Text-to-Speech"
    description = "Convert text to speech using gTTS or ElevenLabs"
    version = "1.0.0"

    def initialize(self):
        """Initialize TTS tool schemas."""
        self.elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "text_to_speech",
                    "description": "Convert text to speech audio",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to convert to speech"
                            },
                            "provider": {
                                "type": "string",
                                "description": "TTS provider",
                                "enum": ["gtts", "elevenlabs", "auto"],
                                "default": "auto"
                            },
                            "language": {
                                "type": "string",
                                "description": "Language code (for gTTS)",
                                "default": "en"
                            },
                            "voice_id": {
                                "type": "string",
                                "description": "Voice ID (for ElevenLabs)",
                                "default": "21m00Tcm4TlvDq8ikWAM"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Where to save audio file",
                                "default": "/tmp/tts_output.mp3"
                            }
                        },
                        "required": ["text"]
                    }
                }
            }
        ]

    def text_to_speech(self, text: str, provider: str = "auto", language: str = "en",
                      voice_id: str = "21m00Tcm4TlvDq8ikWAM",
                      output_path: str = "/tmp/tts_output.mp3") -> Dict[str, Any]:
        """
        Convert text to speech.

        Args:
            text: Text to convert
            provider: TTS provider (gtts or elevenlabs)
            language: Language code
            voice_id: Voice ID for ElevenLabs
            output_path: Where to save audio

        Returns:
            Dict with audio file path and metadata
        """
        # Auto-select provider
        if provider == "auto":
            provider = "elevenlabs" if self.elevenlabs_key else "gtts"

        try:
            if provider == "gtts":
                from utils.tts import generate_tts_gtts
                audio_path = generate_tts_gtts(text, language=language, output_path=output_path)
                return {
                    "audio_path": audio_path,
                    "provider": "gtts",
                    "language": language,
                    "text_length": len(text)
                }

            elif provider == "elevenlabs":
                if not self.elevenlabs_key:
                    return {"error": "ELEVENLABS_API_KEY not configured"}

                from llm_providers.elevenlabs_provider import ElevenLabsProvider
                provider_instance = ElevenLabsProvider(api_key=self.elevenlabs_key)

                # This requires implementation in elevenlabs_provider
                # For now, return placeholder
                return {
                    "error": "ElevenLabs TTS not yet fully implemented",
                    "fallback": "Use gtts provider"
                }

            else:
                return {"error": f"Unknown provider: {provider}"}

        except Exception as e:
            return {"error": f"TTS failed: {str(e)}"}


if __name__ == '__main__':
    TTSTools.main()

