"""
Gemini Provider Package.

Full-featured provider supporting:
- Text generation (chat, completion)
- Vision (image analysis)
- Audio (transcription, analysis)
- Video (analysis up to 6 hours)
- Document processing (PDF up to 50MB)
- Image generation (Imagen)
- Text-to-speech
- Embeddings

Author: Luke Steuber
"""

from .client import GeminiProvider
from .commands import app as gemini_app

__all__ = ["GeminiProvider", "gemini_app"]
