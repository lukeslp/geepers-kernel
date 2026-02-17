# Shared Library (dr-eamer-ai-shared)

The `shared/` directory is the core infrastructure for all LLM-related projects in this monorepo. It provides a unified interface for multiple AI providers, multi-agent orchestration patterns, and structured data fetching.

## Project Overview

This library is published to PyPI as `dr-eamer-ai-shared`. It is designed to be imported by any service or project within the monorepo to ensure consistency and avoid code duplication.

### Key Modules

- **`llm_providers`**: Unified interface for 12+ AI providers (Anthropic, OpenAI, xAI, Mistral, Cohere, Gemini, Perplexity, Groq, HuggingFace, Manus, ElevenLabs, Ollama).
- **`orchestration`**: Frameworks for multi-agent workflows, including `DreamCascadeOrchestrator` (hierarchical) and `DreamSwarmOrchestrator` (parallel).
- **`data_fetching`**: Structured API clients for 17+ sources (arXiv, GitHub, Wikipedia, NASA, etc.).
- **`utils`**: Common utilities for vision, embeddings, file operations, and text processing.
- **`web`**: Helpers for Server-Sent Events (SSE) and web-based streaming.
- **`mcp`**: Tools and helpers for Model Context Protocol integration.

## Building and Running

### Installation
To use this library in a project, it is recommended to install it in editable mode:
```bash
pip install -e /home/coolhand/shared
```

### Development
- **Testing**: Run `pytest` within the `shared/` directory.
- **Linting**: Use `ruff check .` and `black .` for formatting.

## Development Conventions

- **Provider Factory**: Always use `ProviderFactory.get_provider(name)` to instantiate LLM clients.
- **Client Factory**: Use `ClientFactory.create_client(source)` for data fetching.
- **Configuration**: Use `ConfigManager` to load secrets and settings centrally.
- **SSE Streaming**: Follow the established pattern in `shared/web/sse_helpers.py` for real-time updates.

## Key Files
- `llm_providers/`: Adapter implementations for each AI provider.
- `orchestration/`: Orchestrator logic and agent communication patterns.
- `data_fetching/`: API client definitions.
- `config.py`: Centralized configuration management.
