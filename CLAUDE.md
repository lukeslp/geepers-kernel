# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

### Module Overview

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `llm_providers/` | 12 AI provider adapters | `ProviderFactory`, `BaseLLMProvider`, `OllamaProvider` |
| `orchestration/` | Multi-agent workflows | `DreamCascadeOrchestrator`, `DreamSwarmOrchestrator` |
| `data_fetching/` | 17 data source clients | `ClientFactory`, `PubMedClient`, `WolframAlphaClient` |
| `mcp/` | MCP server (port 5060) | `unified_server.py` |
| `document_generation/` | PDF/DOCX/Markdown | `DocumentGenerator` |
| `tools/` | Tool registry for MCP | `ToolModule`, `registry.py` |
| `utils/` | Vision, embeddings, async | `vision.py`, `embeddings.py` |
| `observability/` | Cost tracking, metrics | `CostTracker`, `MetricsCollector` |

### Quick Commands
```bash
pip install -e .[all]                    # Install all providers
pytest                                    # Run tests (91% coverage)
cd mcp && python unified_server.py       # Start MCP server (5060)
black . && isort .                       # Format code
```

## Overview

The `/home/coolhand/shared` directory is a Python library providing reusable AI development infrastructure, published as `dr-eamer-ai-shared`. Core components:

- **LLM Providers** (`llm_providers/`): Unified interface for 12 AI providers (including local Ollama)
- **Orchestration** (`orchestration/`): Multi-agent workflow patterns with streaming
- **MCP Server** (`mcp/`): Model Context Protocol server exposing tools via HTTP
- **Data Clients** (`data_fetching/`): Structured API clients for 17 data sources
- **Document Generation** (`document_generation/`): PDF, DOCX, Markdown output
- **Tools Registry** (`tools/`): Provider-specific tool definitions
- **Utilities** (`utils/`): Vision, embeddings, citation, format conversion, async helpers
- **Observability** (`observability/`): Cost tracking and metrics
- **Configuration** (`config.py`): Multi-source config with API key management

## Commands

```bash
# Install (editable mode)
pip install -e .
pip install -e .[all]              # All providers
pip install -e .[anthropic,xai]    # Specific providers

# Tests
pytest                              # All tests
pytest tests/test_file.py           # Single file
pytest -v -k "test_name"            # Single test by name
pytest --cov=. --cov-report=html    # With coverage

# Run MCP server
cd /home/coolhand/shared/mcp && python unified_server.py   # Port 5060

# Service manager (from parent directory)
/home/coolhand/service_manager.py start mcp-orchestrator
/home/coolhand/service_manager.py status
```

## Architecture

### LLM Providers

All providers implement `BaseLLMProvider` with methods: `complete()`, `stream_complete()`, `generate_image()`, `analyze_image()`.

```python
from llm_providers import ProviderFactory

provider = ProviderFactory.create_provider('xai', api_key='key', model='grok-3')
response = provider.complete(messages=[{'role': 'user', 'content': 'Hello'}])
```

**Complexity Router** (`complexity_router.py`): Auto-selects provider based on task complexity—cheap models for simple tasks, expensive for complex.

### Orchestration Framework

Extend `BaseOrchestrator` and implement 3 methods:
1. `decompose_task()` → `List[SubTask]`
2. `execute_subtask()` → subtask result
3. `synthesize_results()` → `OrchestratorResult`

**Built-in Patterns**:
- `DreamCascadeOrchestrator`: Hierarchical research (Belter → Drummer → Camina tiers)
- `DreamSwarmOrchestrator`: Multi-domain parallel search
- `SequentialOrchestrator`: Staged execution with per-step handlers
- `ConditionalOrchestrator`: Runtime branch selection
- `IterativeOrchestrator`: Looped refinement

See `orchestration/ORCHESTRATOR_GUIDE.md` for implementation details, `ORCHESTRATOR_SELECTION_GUIDE.md` for choosing patterns.

### MCP Server

Main entry point: `mcp/unified_server.py` (port 5060)

**Tools**:
- `dream_orchestrate_research`: Dream Cascade workflow
- `dream_orchestrate_search`: Dream Swarm workflow
- `dreamwalker_status`, `dreamwalker_cancel`: Workflow management
- `dreamwalker_patterns`, `dreamwalker_list_tools`, `dreamwalker_execute_tool`

**SSE Streaming**: `/stream/{task_id}` for real-time progress

Other servers: `providers_server.py`, `data_server.py`, `cache_server.py`, `utility_server.py`

### Data Fetching Clients

```python
from data_fetching import ClientFactory

client = ClientFactory.create_client('arxiv')
results = client.search(query='quantum computing', max_results=10)
```

Available clients: `arxiv`, `census`, `github`, `nasa`, `news`, `openlibrary`, `semantic_scholar`, `weather`, `wikipedia`, `youtube`, `fec`, `judiciary`, `mal`, `archive`, `finance`, `pubmed`, `wolfram`

### Configuration

```python
from config import ConfigManager

config = ConfigManager(app_name='myapp', defaults={'MODEL': 'grok-3'})
api_key = config.get_api_key('xai')
available = config.list_available_providers()
```

Precedence: defaults → config file → `.env` → environment variables → CLI args

## Naming Conventions

**Public branding**: "Dreamwalker" for orchestration tools and MCP servers
- "Dream Cascade" = hierarchical research (formerly "Beltalowda")
- "Dream Swarm" = multi-domain search

`naming.py` provides canonical name mappings. Legacy names (`BeltalowdaOrchestrator`, `SwarmOrchestrator`) are aliased.

## Code Style

- Credit Luke Steuber as author, never "Created with Claude"
- Use first person ("I") in documentation, not "we"
- Type hints required for public APIs
- Store API keys in `/home/coolhand/API_KEYS.md`, load via `ConfigManager`

## Port Allocation

| Service | Port |
|---------|------|
| MCP Server | 5060 |
| Dreamwalker UI | 5080 |
| Dev/Testing | 5010-5019, 5050-5059 |

Caddy proxies `/5010-5019` → `localhost:5010-5019`

## Integration

This library is imported by other projects on this server:
- Web root: `/home/coolhand/html`
- Service manager: `/home/coolhand/service_manager.py`
- Caddy config: `/etc/caddy/Caddyfile`

```python
# From other projects
import sys
sys.path.insert(0, '/home/coolhand/shared')
from llm_providers import ProviderFactory
from orchestration import DreamCascadeOrchestrator
```

## Testing Patterns

### Writing Tests
```python
import pytest
from llm_providers import ProviderFactory

@pytest.mark.asyncio
async def test_provider_completes():
    """Test that provider returns valid response."""
    provider = ProviderFactory.create_provider('xai')
    response = await provider.complete(
        messages=[{'role': 'user', 'content': 'Say hello'}]
    )
    assert response.content
    assert response.usage['output_tokens'] > 0

@pytest.fixture
def mock_provider():
    """Fixture for mocked provider."""
    from unittest.mock import AsyncMock
    provider = AsyncMock()
    provider.complete.return_value = CompletionResponse(
        content="Mocked", model="test", usage={"input_tokens": 1, "output_tokens": 1}
    )
    return provider
```

### Test Commands
```bash
pytest tests/test_orchestrators.py -v      # Specific file
pytest -k "test_dream_cascade"             # By name pattern
pytest -m "not api"                        # Skip API tests
pytest --cov=. --cov-report=html           # Coverage report
```

## Extending the Library

### Adding a New Provider
1. Create `llm_providers/myprovider_provider.py`
2. Extend `BaseLLMProvider`, implement `complete()`, `stream_complete()`
3. Register in `llm_providers/__init__.py`
4. Add tests in `tests/test_providers.py`

### Adding a Data Client
1. Create `data_fetching/myapi_client.py`
2. Implement `search()` returning standardized results
3. Register in `data_fetching/factory.py`
4. Add tests

### Adding a Tool Module
1. Create `tools/mytool_tools.py`
2. Extend `ToolModule`, implement `get_tools()` and `call()`
3. Register in `tools/registry.py`

## Documentation

- `orchestration/ORCHESTRATOR_GUIDE.md` - Implementation guide
- `orchestration/ORCHESTRATOR_SELECTION_GUIDE.md` - Pattern selection
- `orchestration/ORCHESTRATOR_BENCHMARKS.md` - Performance data
- `orchestration/templates/` - Code templates

## Version Control

Repo: `https://github.com/lukeslp/kernel`

Commit format: `type(scope): message` (e.g., `feat(orchestration): add conditional orchestrator`)

Add and commit every 1.5 hours during active development.
