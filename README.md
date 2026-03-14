# geepers-kernel

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/badge/PyPI-geepers--kernel-orange.svg)](https://pypi.org/project/geepers-kernel/)

Core library for the geepers ecosystem. Unified interface to 10+ LLM providers, multi-agent orchestration patterns, 15+ structured data API clients, and MCP server infrastructure.

**Documentation:** [dr.eamer.dev/geepers](https://github.com/lukeslp/geepers-kernel)  
**Author:** Luke Steuber

---

## Install

```bash
pip install geepers-kernel

# With all provider dependencies
pip install geepers-kernel[all]

# Specific providers
pip install geepers-kernel[anthropic,xai,openai]
```

Or from source:

```bash
git clone https://github.com/lukeslp/geepers-kernel.git
cd geepers-kernel
pip install -e .[all]
```

---

## Quick start

### LLM providers

```python
from llm_providers import ProviderFactory

provider = ProviderFactory.create_provider('xai', model='grok-3')
response = provider.complete(messages=[
    {'role': 'user', 'content': 'Explain quantum computing'}
])
print(response)
```

### Multi-agent research (Dream Cascade)

```python
from orchestration import DreamCascadeOrchestrator

orchestrator = DreamCascadeOrchestrator(
    provider_name='anthropic',
    model='claude-sonnet-4'
)

result = await orchestrator.execute(
    task="LLM safety research 2023-2025",
    enable_drummer=True,  # mid-level synthesis
    enable_camina=True    # executive summary
)

print(result.final_report)
```

### Data fetching

```python
from data_fetching import ClientFactory

arxiv = ClientFactory.create_client('arxiv')
papers = arxiv.search(query='quantum computing', max_results=10)

census = ClientFactory.create_client('census_acs')
data = census.get_demographics(geography='state:06')
```

---

## LLM providers

| Provider | Chat | Vision | Image Gen |
|----------|------|--------|-----------|
| Anthropic (Claude) | ✓ | ✓ | , |
| OpenAI (GPT-4) | ✓ | ✓ | ✓ |
| xAI (Grok) | ✓ | ✓ | ✓ |
| Mistral | ✓ | ✓ | , |
| Cohere | ✓ | , | , |
| Google (Gemini) | ✓ | ✓ | , |
| Perplexity | ✓ | ✓ | , |
| Groq (Llama) | ✓ | , | , |
| HuggingFace | ✓ | ✓ | ✓ |
| DeepSeek | ✓ | , | , |

Complexity router selects models automatically based on task requirements.

---

## Orchestration patterns

| Pattern | What it does |
|---------|-------------|
| `dream-cascade` | Hierarchical: 8 parallel workers → Drummer synthesis → Camina executive summary |
| `dream-swarm` | Parallel: 5+ domain-specific agents (Academic, News, Technical, Financial) |
| `sequential` | Staged execution with per-step handlers |
| `conditional` | Runtime branch selection |
| `iterative` | Refinement loops with success predicates |

---

## Data sources (15+)

- **Academic**: arXiv, Semantic Scholar, Open Library, Wikipedia
- **News**: NewsAPI, YouTube
- **Code**: GitHub repos, commits, users
- **Government**: US Census ACS, SAIPE poverty estimates
- **Science**: NASA (APOD, Mars photos, satellite imagery)
- **Weather**: current conditions, forecasts, air quality
- **Finance**: stock quotes, company fundamentals

---

## MCP servers

Four MCP servers expose the library's capabilities via stdio/HTTP:

- `geepers-unified` , orchestration (Dream Cascade, Dream Swarm)
- `geepers-providers` , direct LLM provider access
- `geepers-data` , data fetching tools
- `geepers-websearch` , web search (Brave, SerpAPI)

See [MCP Guide](https://github.com/lukeslp/geepers-kernelmcp/) for configuration.

---

## Package structure

```
geepers-kernel/
├── llm_providers/          # provider implementations + ProviderFactory
├── orchestration/          # Dream Cascade, Dream Swarm, Sequential, Conditional, Iterative
├── mcp/                    # MCP server implementations
├── data_fetching/          # structured API clients (dream_of_*)
├── document_generation/    # PDF, DOCX, Markdown output
├── config.py               # multi-source configuration
└── naming.py               # naming registry
```

### Naming convention

| Pattern | Prefix | Examples |
|---------|--------|----------|
| Orchestration workflows | `dream-*` | `dream-cascade`, `dream-swarm` |
| Data tools | `dream_of_*` | `dream_of_arxiv`, `dream_of_census_acs` |
| Management tools | `geepers_*` | `geepers_status`, `geepers_cancel` |

---

## Configuration

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

# Data sources
YOUTUBE_API_KEY=...
GITHUB_TOKEN=ghp_...
NASA_API_KEY=...
NEWS_API_KEY=...

# Infrastructure
REDIS_HOST=localhost
REDIS_PORT=6379
```

Configuration precedence: defaults → `.env` → environment variables → CLI args

---

## Testing

```bash
pytest
pytest --cov=. --cov-report=html
pytest tests/test_providers.py
```

---

## License

MIT © Luke Steuber
