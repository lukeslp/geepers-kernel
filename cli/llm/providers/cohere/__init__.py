"""
Cohere Provider Package.

Supports:
- Text generation (Command R+, Command R)
- Embeddings (Embed v3)

Author: Luke Steuber
"""

from .client import CohereProvider
from .commands import app as cohere_app

__all__ = ["CohereProvider", "cohere_app"]
