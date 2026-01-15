"""
OpenAI Provider Package.

Supports:
- Text generation (GPT-4o, GPT-4, o1)
- Vision (GPT-4o, GPT-4o-mini)
- Audio transcription (Whisper)
- Image generation (DALL-E 3, DALL-E 2)
- Text-to-speech (TTS-1, TTS-1-HD)
- Embeddings (text-embedding-3)

Author: Luke Steuber
"""

from .client import OpenAIProvider
from .commands import app as openai_app

__all__ = ["OpenAIProvider", "openai_app"]
