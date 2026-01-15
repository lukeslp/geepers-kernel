"""
Mistral Provider Package.

Supports:
- Text generation (Mistral Large, Medium, Small, Codestral)
- Vision (Pixtral)
- Embeddings

Author: Luke Steuber
"""

from .client import MistralProvider
from .commands import app as mistral_app

__all__ = ["MistralProvider", "mistral_app"]
