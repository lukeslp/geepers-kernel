"""
Core unified commands for LLM CLI.

These commands auto-select the best available provider for each task.

Author: Luke Steuber
"""

from .chat import unified_chat
from .vision import unified_vision
from .audio import unified_audio
from .embed import unified_embed, batch_embed
from .models import list_models, show_provider_status, get_model_info

__all__ = [
    "unified_chat",
    "unified_vision",
    "unified_audio",
    "unified_embed",
    "batch_embed",
    "list_models",
    "show_provider_status",
    "get_model_info",
]
