# geepers-core

Foundation library for all LLM tooling on dr.eamer.dev. 14 providers, 18 data clients, Dream Cascade/Swarm orchestrators, MCP server infrastructure.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI: geepers-core](https://img.shields.io/badge/PyPI-geepers--core-orange.svg)](https://pypi.org/project/geepers-core/)

Previously published as `dr-eamer-ai-shared`.

## Install

```bash
pip install -e .[all]                   # All provider dependencies
pip install -e .[anthropic,xai]         # Specific providers only
pip install geepers-core[all]           # From PyPI
```

## Usage

```python
import sys
sys.path.insert(0, '/home/coolhand/shared')

from llm_providers import ProviderFactory
from orchestration import DreamCascadeOrchestrator
from data_fetching import ClientFactory
from config import ConfigManager
```

**LLM chat:**
```python
provider = ProviderFactory.create_provider('xai', model='grok-3')
response = provider.complete(messages=[{'role': 'user', 'content': 'hello'}])
```

**Research orchestration:**
```python
orchestrator = DreamCascadeOrchestrator(provider_name='anthropic', model='claude-sonnet-4-5')
result = await orchestrator.execute(task="LLM safety research 2024-2025")
print(result.final_report)
```

**Data fetching:**
```python
arxiv = ClientFactory.create_client('arxiv')
papers = arxiv.search(query='quantum computing', max_results=10)
```

## What's in the box

**LLM Providers (14):** Anthropic, OpenAI, xAI, Mistral, Cohere, Gemini, Perplexity, Groq, HuggingFace, Manus, ElevenLabs, Ollama, Gradient, ClaudeCode — unified interface via `ProviderFactory`.

**Orchestration:** Dream Cascade (8 parallel agents → mid synthesis → executive summary), Dream Swarm (parallel domain-specific agents). Legacy names `BeltalowdaOrchestrator` / `SwarmOrchestrator` still work via `naming.py`.

**Data Clients (18):** arXiv, Semantic Scholar, Wikipedia, PubMed, GitHub, NASA, Census ACS/SAIPE, NewsAPI, YouTube, OpenLibrary, Weather, Finance, FEC, Judiciary, Wolfram Alpha, Wayback Machine.

**MCP Server:** Runs on port 5060, exposes all tools via HTTP/SSE and stdio. `sm start mcp-orchestrator`.

**Web components:** Flask blueprints for LLM proxy, auth, CORS, rate limiting, health endpoints.

**Utilities:** Vision, embeddings, document generation (PDF/DOCX/Markdown), TTS, multi-search, citations, retry logic, async adapters.

## Configuration

API keys from `~/.env` or environment variables. Key vars: `XAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`, `GEMINI_API_KEY`.

```python
from config import ConfigManager
config = ConfigManager(app_name='myapp')
key = config.get_api_key('xai')
```

## Tests

```bash
pytest                                    # All tests
pytest tests/test_providers.py -v        # Single file
pytest -v -k "test_anthropic"            # Single test
```

## MCP server

```bash
cd /home/coolhand/shared/mcp && python unified_server.py   # port 5060
sm start mcp-orchestrator
```

## Author

**Luke Steuber** · [lukesteuber.com](https://lukesteuber.com) · [@lukesteuber.com](https://bsky.app/profile/lukesteuber.com)

MIT License · [github.com/lukeslp/kernel](https://github.com/lukeslp/kernel)
