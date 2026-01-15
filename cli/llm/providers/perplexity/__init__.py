"""
Perplexity Provider Package.

Supports:
- Text generation with citations (Sonar, Sonar Pro)

Author: Luke Steuber
"""

from .client import PerplexityProvider
from .commands import app as perplexity_app

__all__ = ["PerplexityProvider", "perplexity_app"]
