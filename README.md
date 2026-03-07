# geepers-kernel

**Unified LLM Development Infrastructure**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI: geepers-kernel](https://img.shields.io/badge/PyPI-geepers--kernel-orange.svg)](https://pypi.org/project/geepers-kernel/)
[![Status: Production](https://img.shields.io/badge/status-production-brightgreen.svg)]()

---

## Overview

`geepers-kernel` is the core library behind the Dreamwalker MCP ecosystem. It provides:

- **10+ LLM Providers** — Unified interface for Anthropic, OpenAI, xAI, Mistral, Cohere, Gemini, Perplexity, Groq, and more
- **Multi-Agent Orchestration** — Dream Cascade (hierarchical research) and Dream Swarm (parallel search) patterns
- **15+ Data Sources** — Structured API clients for arXiv, Semantic Scholar, Census, GitHub, NASA, and more
- **MCP Server Infrastructure** — Model Context Protocol servers exposing tools via stdio/HTTP
- **Document Generation** — PDF, DOCX, and Markdown output with citations

**Status:** Production-ready, actively developed  
**Package Name:** `geepers-kernel` *(published on PyPI)*  
**Documentation:** [dr.eamer.dev/dreamwalker](https://dr.eamer.dev/dreamwalker/)

---

## Quick Start

### Installation

```bash
# Clone and install in editable mode
git clone https://github.com/lukeslp/kernel
cd kernel/shared
pip install -e .

# Install with all provider dependencies
pip install -e .[all]

# Install specific providers only
pip install -e .[anthropic,xai,openai]
```

### Basic Usage

**1. LLM Provider Abstraction**

```python
from llm_providers import ProviderFactory

# Unified interface across 10+ providers
provider = ProviderFactory.create_provider('xai', model='grok-3')
response = provider.complete(messages=[
    {'role': 'user', 'content': 'Explain quantum computing'}
])
print(response)
```

**2. Multi-Agent Research (Dream Cascade)**

```python
from orchestration import DreamCascadeOrchestrator

# Hierarchical research with 8 agents
orchestrator = DreamCascadeOrchestrator(
    provider_name='anthropic',
    model='claude-sonnet-4'
)

result = await orchestrator.execute(
    task="Comprehensive analysis of LLM safety research 2023-2025",
    enable_drummer=True,  # Mid-level synthesis
    enable_camina=True    # Executive summary
)

print(result.final_report)
```

**3. Data Fetching (dream_of_* tools)**

```python
from data_fetching import ClientFactory

# Academic papers
arxiv = ClientFactory.create_client('arxiv')
papers = arxiv.search(query='quantum computing', max_results=10)

# US Census demographics
census = ClientFactory.create_client('census_acs')
data = census.get_demographics(geography='state:06')  # California
```

---

## Architecture

### Dreamwalker Naming Convention

The library uses **semantic, descriptive naming** (moved away from codename-based naming in November 2025):

| Pattern | Prefix | Examples |
|---------|--------|----------|
| **Orchestration Workflows** | `dream-*` | `dream-cascade`, `dream-swarm` |
| **Data Tools** | `dream_of_*` | `dream_of_arxiv`, `dream_of_census_acs` |
| **Management Tools** | `dreamwalker_*` | `dreamwalker_status`, `dreamwalker_cancel` |
| **Provider Tools** | `dreamer_*` | `dreamer_anthropic`, `dreamer_openai` (deferred) |

**Classes:**
- `DreamCascadeOrchestrator` — Implements dream-cascade pattern (hierarchical research)
- `DreamSwarmOrchestrator` — Implements dream-swarm pattern (parallel search)

### Package Structure

```
shared/
├── llm_providers/          # 10+ provider implementations
│   ├── base_provider.py    # BaseLLMProvider abstract class
│   ├── factory.py          # ProviderFactory
│   ├── anthropic_provider.py
│   ├── openai_provider.py
│   ├── xai_provider.py
│   └── ...
├── orchestration/          # Multi-agent workflow patterns
│   ├── dream_cascade.py    # Hierarchical research
│   ├── dream_swarm.py      # Parallel search
│   ├── sequential.py       # Staged execution
│   ├── conditional.py      # Branching logic
│   └── iterative.py        # Refinement loops
├── mcp/                    # Model Context Protocol servers
│   ├── unified_server.py   # Main orchestration (port 5060)
│   ├── providers_server.py
│   ├── data_server.py
│   └── ...
├── data_fetching/          # 15+ structured API clients
│   ├── dream_of_arxiv.py
│   ├── dream_of_semantic_scholar.py
│   ├── dream_of_census_acs.py
│   └── ...
├── document_generation/    # PDF, DOCX, Markdown output
├── config.py               # Multi-source configuration
└── naming.py               # Naming registry
```

---

## Features

### LLM Providers (10+)

Unified interface across providers with automatic model selection, cost tracking, and failover:

- **Anthropic** — Claude Opus, Sonnet, Haiku
- **OpenAI** — GPT-4, GPT-4-Turbo, DALL-E 3
- **xAI** — Grok-3, Grok-3-mini, Aurora (vision + image gen)
- **Mistral** — Large, Medium, Small
- **Cohere** — Command R+
- **Google** — Gemini Pro, Ultra
- **Perplexity** — pplx-70b-online (web search)
- **Groq** — Llama 3.1 (ultra-fast inference)
- **HuggingFace** — Various open models
- **DeepSeek** — R1 reasoning model

**Complexity Router:** Automatically selects cheap models for simple tasks, expensive for complex.

### Orchestration Patterns

**dream-cascade** (Hierarchical Research)
- 8 parallel workers (specialized agents)
- Mid-level synthesis (Drummer)
- Executive synthesis (Camina)
- Use case: Academic literature reviews, market research, due diligence

**dream-swarm** (Parallel Search)
- 5+ specialized agents execute in parallel
- Domain-specific: Academic, News, Technical, Financial
- Use case: Broad exploratory research, competitive analysis

**Sequential/Conditional/Iterative**
- Staged execution with per-step handlers
- Runtime branch selection
- Looped refinement with success predicates

### Data Sources (15+)

**Academic & Research:**
- `dream_of_arxiv` — Academic papers
- `dream_of_semantic_scholar` — Citation analysis
- `dream_of_openlibrary` — Book metadata
- `dream_of_wikipedia` — Encyclopedia summaries

**News & Media:**
- `dream_of_news` — News articles (NewsAPI)
- `dream_of_youtube` — Video metadata

**Technical & Code:**
- `dream_of_github` — Repository data, commits, users

**Government & Demographics:**
- `dream_of_census_acs` — US Census American Community Survey
- `dream_of_census_saipe` — Poverty estimates

**Science & Space:**
- `dream_of_nasa` — APOD, Mars photos, Earth imagery

**Location & Weather:**
- Weather current conditions, forecasts, air quality

**Finance:**
- Stock quotes, company fundamentals

### Document Generation

Professional output in multiple formats:
- **PDF** — With citations, table of contents, formatting
- **DOCX** — Editable Microsoft Word format
- **Markdown** — Portable, version-control friendly

---

## Configuration

### API Keys

Create `.env` file or export environment variables:

```bash
# Core providers (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
XAI_API_KEY=xai-...

# Optional providers
MISTRAL_API_KEY=...
COHERE_API_KEY=...
GEMINI_API_KEY=...
PERPLEXITY_API_KEY=...
GROQ_API_KEY=...

# Data sources (optional)
YOUTUBE_API_KEY=...
GITHUB_TOKEN=ghp_...
NASA_API_KEY=...
NEWS_API_KEY=...

# Infrastructure (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Configuration Precedence

```
defaults → .app file → .env → environment variables → CLI args
(lowest priority)                                    (highest priority)
```

---

## MCP Integration

### Running MCP Servers

```bash
# Main orchestration server (port 5060)
cd /home/coolhand/shared/mcp
python unified_server.py

# Or via service manager
/home/coolhand/service_manager.py start mcp-orchestrator
```

### Available MCP Tools

**Orchestration:**
- `dream_research` — Dream Cascade hierarchical research
- `dream_search` — Dream Swarm parallel search

**Management:**
- `dreamwalker_status` — Check workflow progress
- `dreamwalker_cancel` — Stop running workflows
- `dreamwalker_patterns` — List available patterns

**Data Fetching:**
- `dream_of_arxiv`, `dream_of_census_acs`, `dream_of_github`, etc.

See [MCP Guide](https://dr.eamer.dev/shared/mcp-guide.html) for comprehensive documentation.

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_providers.py

# Run single test
pytest -v -k "test_anthropic_provider"
```

**Current Coverage:** 91%

---

## Development

### Code Style

- **Black** — Code formatting (100 char lines)
- **isort** — Import sorting
- **Type hints** — Required for public APIs
- **Docstrings** — Google style

### Pre-commit Hooks

```bash
# Install hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Documentation

**Comprehensive Guides:**
- [Provider Matrix](https://dr.eamer.dev/shared/provider-matrix.html) — LLM provider comparison
- [Data Fetching Guide](https://dr.eamer.dev/shared/data-fetching.html) — Data source catalog
- [Vision Guide](https://dr.eamer.dev/shared/vision-guide.html) — Image analysis and generation
- [MCP Guide](https://dr.eamer.dev/shared/mcp-guide.html) — MCP server reference
- [Documentation Hub](https://dr.eamer.dev/shared/) — Central navigation

**In-Repo Docs:**
- `CLAUDE.md` — Repository guide for Claude Code
- `orchestration/ORCHESTRATOR_GUIDE.md` — Building custom orchestrators
- `orchestration/ORCHESTRATOR_SELECTION_GUIDE.md` — Choosing patterns
- `orchestration/ORCHESTRATOR_BENCHMARKS.md` — Performance data

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with clear commit messages
4. Add tests for new features
5. Update documentation as needed
6. Run tests: `pytest tests/`
7. Submit a Pull Request

**Areas that could use help:**
- New orchestrator patterns (graph-based, recursive, hybrid)
- Additional data sources (more API clients)
- Provider integrations (new LLM providers)
- Performance optimizations (caching strategies)
- Documentation improvements (tutorials, examples)
- Testing (integration tests, edge cases)

---

## License

MIT License

Copyright (c) 2025 Luke Steuber

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Acknowledgments

Built with:
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [Claude](https://www.anthropic.com/) by Anthropic
- [OpenAI GPT](https://openai.com/)
- [xAI Grok](https://x.ai/)
- And many other open-source libraries (see `requirements.txt`)

**Author:** Luke Steuber  
**Repository:** [github.com/lukeslp/kernel](https://github.com/lukeslp/kernel)  
**Website:** [dr.eamer.dev](https://dr.eamer.dev)

---






