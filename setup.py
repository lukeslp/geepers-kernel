"""
Setup configuration for the shared library.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="dr-eamer-ai-shared",
    version="1.0.0",
    description="Shared library for AI development projects - LLM providers, config management, and utilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Luke Steuber",
    author_email="luke@lukesteuber.com",
    url="https://github.com/lukeslp/kernel",
    project_urls={
        "Homepage": "https://dr.eamer.dev",
        "Documentation": "https://dr.eamer.dev/shared/",
        "Source": "https://github.com/lukeslp/kernel/tree/master/shared",
        "Bug Reports": "https://github.com/lukeslp/kernel/issues",
        "Changelog": "https://github.com/lukeslp/kernel/blob/master/shared/CLAUDE.md",
    },
    packages=find_packages(),
    python_requires=">=3.8",
    license="MIT",
    keywords=[
        "llm", "ai", "artificial-intelligence", "utilities", "anthropic", "openai", 
        "xai", "grok", "claude", "gpt", "mistral", "cohere", "gemini",
        "mcp", "model-context-protocol", "configuration", "providers"
    ],
    install_requires=[
        # Core dependencies
        "python-dotenv>=1.0.0",
        "requests>=2.32.5",  # Security: CVE-2024-47081, CVE-2024-35195
        "pillow>=11.0.0",
        # Phase 1 utilities dependencies
        "arxiv>=2.0.0",  # ArXiv client
        "gtts>=2.5.0",  # Text-to-speech
        "bibtexparser>=1.4.0",  # Citation management
        "aiohttp>=3.12.14",  # Async HTTP for SemanticScholar
    ],
    extras_require={
        "anthropic": ["anthropic>=0.71.0"],
        "openai": ["openai>=2.0.0"],
        "xai": ["openai>=2.0.0"],  # xAI uses OpenAI-compatible API
        "mistral": ["mistralai>=1.0.0"],
        "cohere": ["cohere>=5.15.0"],
        "gemini": ["google-generativeai>=0.8.0"],
        "perplexity": ["openai>=2.0.0"],  # Perplexity uses OpenAI-compatible API
        "groq": ["openai>=2.0.0"],  # Groq uses OpenAI-compatible API
        "huggingface": ["huggingface-hub>=0.20.0"],
        "redis": ["redis>=7.0.0"],
        "telemetry": [
            "opentelemetry-api>=1.21.0",
            "opentelemetry-sdk>=1.21.0",
        ],
        "all": [
            "python-dotenv>=1.0.0",
            "anthropic>=0.71.0",
            "openai>=2.0.0",
            "requests>=2.32.5",
            "pillow>=11.0.0",
            "mistralai>=1.0.0",
            "cohere>=5.15.0",
            "google-generativeai>=0.8.0",
            "huggingface-hub>=0.20.0",
            "redis>=7.0.0",
            "opentelemetry-api>=1.21.0",
            "opentelemetry-sdk>=1.21.0",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
        "Typing :: Typed",
        "Framework :: AsyncIO",
    ],
)
