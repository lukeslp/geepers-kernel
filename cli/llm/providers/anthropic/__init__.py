"""
Anthropic Provider Package.

Supports:
- Text generation (Claude Sonnet 4, Opus 4, Claude 3.5 series)
- Vision (all Claude models with vision capability)

Author: Luke Steuber
"""

from .client import AnthropicProvider
from .commands import app as anthropic_app

__all__ = ["AnthropicProvider", "anthropic_app"]
