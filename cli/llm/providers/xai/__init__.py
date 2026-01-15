"""
xAI Provider Package.

Supports:
- Text generation (Grok-3, Grok-3-fast, Grok-2)
- Vision (Grok-2-vision)
- Image generation (Aurora)

Author: Luke Steuber
"""

from .client import XAIProvider
from .commands import app as xai_app

__all__ = ["XAIProvider", "xai_app"]
