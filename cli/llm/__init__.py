"""
Unified LLM CLI Suite

A comprehensive command-line interface for multiple LLM providers including
Gemini, OpenAI, Anthropic, xAI, Mistral, Cohere, and Perplexity.

Author: Luke Steuber
"""

__version__ = "0.1.0"
__author__ = "Luke Steuber"

from .main import app

__all__ = ["app", "__version__"]
