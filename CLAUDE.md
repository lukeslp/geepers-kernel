# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

```bash
# Install
pip install -e .                         # Core only
pip install -e .[all]                    # All provider dependencies
pip install -e .[anthropic,xai]          # Specific providers

# Tests
pytest                                    # All tests
pytest tests/test_file.py -v             # Single file
pytest -v -k "test_name"                 # Single test by name
pytest --cov=. --cov-report=html         # Coverage report

# Formatting
black . && isort .

# MCP server
cd /home/coolhand/shared/mcp && python unified_server.py   # Port 5060

# Service manager
/home/coolhand/service_manager.py start mcp-orchestrator
/home/coolhand/service_manager.py status
```

## Overview

Python library published as **`geepers-core`** (PyPI, v1.0.2). Previously `dr-eamer-ai-shared`. `setup.py` has been removed — `pyproject.toml` is the sole build config. Provides reusable LLM, orchestration, data fetching, and web infrastructure for all projects on dr.eamer.dev.

**Each module has its own CLAUDE.md** with detailed API docs and code examples. This file covers cross-cutting architecture and what you need to know across modules.

## Architecture

### How Modules Connect

```
config.py ──────────────────────────────────────── ConfigManager (API keys, env vars)
    │
    ├── llm_providers/  ── ProviderFactory ──────── BaseLLMProvider implementations
    │       │                                        (14 providers: anthropic, openai, xai,
    │       │                                         mistral, cohere, gemini, perplexity,
    │       │                                         groq, huggingface, manus, elevenlabs,
    │       │                                         ollama, gradient, claude_code)
    │       │
    │       ├── complexity_router.py ──── Routes tasks to cheap/mid/expensive providers
    │       └── tiered_selector.py ────── Model selection by tier
    │
    ├── orchestration/  ── BaseOrchestrator ─────── 3-step pattern: decompose → execute → synthesize
    │       │                                        Uses llm_providers for LLM calls
    │       ├── dream_cascade_orchestrator.py ───── Hierarchical research (3 tiers)
    │       ├── dream_swarm_orchestrator.py ──────── Parallel multi-domain search
    │       ├── sequential/conditional/iterative ── Other patterns
    │       └── dreamer_*.py ──────────────────────── Legacy aliases
    │
    ├── data_fetching/  ── ClientFactory ─────────── 18 API clients (arxiv, census, github,
    │       │                                         nasa, news, wikipedia, pubmed, wolfram,
    │       │                                         semantic_scholar, weather, youtube,
    │       │                                         openlibrary, finance, fec, judiciary,
    │       │                                         mal, archive)
    │       │
    ├── tools/  ── ToolRegistry ──────────────────── Wraps providers + data_fetching as MCP tools
    │       │      ToolModuleBase / DataToolModuleBase
    │       ├── Provider tools (openai_tools, anthropic_tools, xai_tools, etc.)
    │       ├── Data tools (arxiv_tool, github_tool, nasa_tool, etc.)
    │       ├── gradient_tools.py ────────────────── DigitalOcean Gradient AI
    │       └── monarchmoney/ ────────────────────── Financial tool (separate subpackage)
    │
    ├── mcp/  ── unified_server.py (port 5060) ──── MCP server exposing tools via HTTP/SSE
    │       ├── stdio_server.py ──────────────────── STDIO MCP transport
    │       ├── master_server.py ─────────────────── Multi-server coordinator
    │       ├── providers_server.py ──────────────── LLM provider tools
    │       ├── data_server.py ───────────────────── Data fetching tools
    │       ├── web_search_server.py ─────────────── Web search tools
    │       ├── cache_server.py ──────────────────── Response caching
    │       └── streaming.py + background_loop.py ── SSE streaming + async execution
    │
    ├── remote_mcp/  ── server.py (port 5061) ──── FastMCP wrapper for remote HTTP/Streamable access
    │       └── Caddy route: /mcp-remote/ ──────── Claude Desktop Custom Connector endpoint
    │
    ├── web/  ── Flask components ────────────────── Reusable Flask blueprints and middleware
    │       ├── llm_proxy_blueprint.py ───────────── Unified LLM proxy (POST /complete, /stream, /vision)
    │       ├── universal_proxy.py ───────────────── Generic HTTP proxy
    │       ├── auth.py ──────────────────────────── Bearer token + signed token auth
    │       ├── cors_config.py, rate_limit.py ────── CORS + rate limiting
    │       ├── health.py ────────────────────────── Health check endpoint factory
    │       └── middleware.py ─────────────────────── Request logging, error handlers, correlation IDs
    │
    ├── document_generation/  ────────────────────── PDF (ReportLab), DOCX (python-docx), Markdown
    │
    ├── utils/  ──────────────────────────────────── Vision, embeddings, citations, document parsers,
    │                                                 async adapters, retry logic, rate limiting,
    │                                                 text processing, file utils, format converter,
    │                                                 multi-search, data validation, TTS, crypto
    │
    ├── observability/  ──────────────────────────── CostTracker, MetricsCollector
    │
    ├── cli/  ────────────────────────────────────── CLI tool infrastructure
    ├── api_auth/  ───────────────────────────────── API authentication utilities
    ├── memory/  ─────────────────────────────────── Memory and caching (Redis)
    └── naming.py  ───────────────────────────────── Canonical name registry + legacy aliases
```

### Key Design Patterns

**Provider Factory (Singleton + Lazy Loading)**:
`ProviderFactory.get_provider('xai')` returns a cached singleton. `create_provider()` creates a fresh instance. All providers implement `BaseLLMProvider` with `complete()`, `stream_complete()`, optional `generate_image()`, `analyze_image()`.

**Orchestrator 3-Step Pattern**:
All orchestrators extend `BaseOrchestrator` and implement: `decompose_task() -> List[SubTask]`, `execute_subtask() -> AgentResult`, `synthesize_results() -> OrchestratorResult`. Dream Cascade uses 3 tiers (Belter/Drummer/Camina). Dream Swarm runs domain-specific agents in parallel.

**Tool Registry (Singleton)**:
`tools/registry.py` provides `get_registry()` singleton. Tools are MCP-schema-compatible dicts with `name`, `description`, `inputSchema`. Both `ToolModuleBase` (provider tools) and `DataToolModuleBase` (data tools) register into this registry, which the MCP server then exposes.

**Config Precedence**:
`config.py` → `ConfigManager` loads from: defaults < config file < `.env` < environment variables < CLI args. API keys come from `/home/coolhand/documentation/API_KEYS.md` or environment.

### Naming Conventions

**Public branding**: "Dreamwalker" for orchestration/MCP tools.
- "Dream Cascade" = hierarchical research (legacy: "Beltalowda")
- "Dream Swarm" = parallel search
- Data tools prefixed `dream_of_*` (e.g., `dream_of_arxiv`)
- Management tools prefixed `dreamwalker_*`

`naming.py` maps legacy class names to current ones. Legacy aliases (`BeltalowdaOrchestrator`, `SwarmOrchestrator`, `DreamerBeltalowdaOrchestrator`) still work.

## Integration

This library is the foundation for all projects on dr.eamer.dev:

```python
# From other projects
import sys
sys.path.insert(0, '/home/coolhand/shared')

from llm_providers import ProviderFactory
from orchestration import DreamCascadeOrchestrator
from data_fetching import ClientFactory
from config import ConfigManager
from web import create_health_endpoint, setup_cors
```

## Port Allocation

| Service | Port |
|---------|------|
| MCP Server (unified_server.py) | 5060 |
| Remote MCP Server (remote_mcp/server.py) | 5061 |
| Dreamwalker UI | 5080 |
| Dev/Testing | 5010-5019, 5050-5059 |

## Tests

17 test files in `tests/`:

| File | Tests |
|------|-------|
| `test_providers.py` | LLM provider factory and completion |
| `test_ollama_provider.py` | Local Ollama provider |
| `test_orchestrators.py` | Orchestrator patterns |
| `test_data_tool_modules.py` | Data fetching tool wrappers |
| `test_tool_registry.py` | Tool registration and execution |
| `test_provider_tools.py` | Provider tool modules |
| `test_vision.py`, `test_image_vision.py` | Vision utilities |
| `test_embeddings.py` | Embedding generation |
| `test_document_parsers.py` | PDF/DOCX/TXT parsing |
| `test_multi_search.py` | Parallel search |
| `test_shared_imports.py` | Package import validation |
| `test_time_utils.py` | Time utilities |
| `test_utils_enhancements.py` | General utility tests |
| `test_workflow_state.py` | Workflow state management |
| `test_dreamwalker_app.py` | Dreamwalker web app |

## Extending the Library

### Adding a New LLM Provider
1. Create `llm_providers/myprovider_provider.py` extending `BaseLLMProvider`
2. Implement `complete()`, `stream_complete()`, optionally `generate_image()`, `analyze_image()`
3. Register in `llm_providers/factory.py` (add to `PROVIDER_CAPABILITIES` and provider map)
4. Update `llm_providers/__init__.py` exports
5. Add tests in `tests/test_providers.py`

### Adding a Data Client
1. Create `data_fetching/myapi_client.py` with `search()` returning standardized results
2. Register in `data_fetching/factory.py` `CLIENT_REGISTRY`
3. Export in `data_fetching/__init__.py`
4. Optionally create `tools/myapi_tool.py` extending `DataToolModuleBase` for MCP exposure

### Adding a Tool Module
1. Create `tools/mytool_tools.py` extending `ToolModuleBase`
2. Implement `get_tools()` (returns MCP-compatible schemas) and `call()` (executes tool)
3. Register in `tools/registry.py`

## Code Style

- **Author**: Luke Steuber - never credit "Claude" or use "AI-powered/AI-driven" language
- **First person** ("I") in documentation, not "we"
- **Type hints** required for public APIs
- **Black** formatting (100 char lines), **isort** for imports
- **Commit format**: `type(scope): message` (e.g., `feat(orchestration): add conditional orchestrator`)
- API keys: load via `ConfigManager`, store in `/home/coolhand/documentation/API_KEYS.md`

## Documentation

Each module has its own `CLAUDE.md` with full API docs:
- `llm_providers/CLAUDE.md` - Provider interface, data classes, examples for all 14 providers
- `orchestration/CLAUDE.md` - All orchestrator patterns with code examples
- `data_fetching/CLAUDE.md` - All 18 client APIs with usage examples
- `mcp/CLAUDE.md` - MCP server endpoints, tools, SSE streaming
- `tools/CLAUDE.md` - Tool registry, module base classes, provider/data tools
- `utils/CLAUDE.md` - All 16 utility modules with examples
- `web/CLAUDE.md` - Flask blueprints, auth, CORS, rate limiting, proxy
- `document_generation/CLAUDE.md` - PDF/DOCX/Markdown generators

Additional guides:
- `orchestration/ORCHESTRATOR_GUIDE.md` - Building custom orchestrators
- `orchestration/ORCHESTRATOR_SELECTION_GUIDE.md` - Choosing patterns
- `orchestration/ORCHESTRATOR_BENCHMARKS.md` - Performance data

## Version Control

Repo: `https://github.com/lukeslp/geepers-kernel`
