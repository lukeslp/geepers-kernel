# geepers-kernel

[![PyPI](https://img.shields.io/pypi/v/geepers-kernel.svg)](https://pypi.org/project/geepers-kernel/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Core infrastructure for the [geepers](https://github.com/lukeslp/geepers) multi-agent system. Gives you a single unified interface to 14 LLM providers, two orchestration patterns for multi-agent workflows, 18 structured data clients, an MCP server, and reusable Flask utilities — all installable with one `pip install`.

Previously published as `geepers-core` and `dr-eamer-ai-shared`. Running in production at [dr.eamer.dev](https://dr.eamer.dev).

---

## Install

```bash
# All provider SDKs included
pip install geepers-kernel[all]

# Pick only what you need
pip install geepers-kernel[anthropic,xai]

# Core only — no provider SDKs, useful if you're bringing your own
pip install geepers-kernel
```

Optional extras: `anthropic`, `openai`, `xai`, `mistral`, `cohere`, `gemini`, `perplexity`, `groq`, `huggingface`, `redis`, `telemetry`

> **Note:** The package imports as `shared.*` (not as `geepers_kernel`). Running from a local clone? Add the repo root to your path first — the quick start examples below show how.

---

## Quick start

```python
import sys
sys.path.insert(0, '/path/to/geepers-kernel')  # skip if installed via pip

from shared.llm_providers import ProviderFactory, Message

# Chat with any provider using the same interface
provider = ProviderFactory.get_provider('xai')
response = provider.complete(
    messages=[Message(role='user', content='Explain transformer attention in one paragraph')]
)
print(response.content)
print(f"Tokens used: {response.usage}")
```

```python
# Stream a response
for chunk in provider.stream_complete(messages=[Message(role='user', content='Count to 5')]):
    print(chunk.content, end='', flush=True)
```

```python
# Swap providers — same call, different model
claude  = ProviderFactory.get_provider('anthropic')
gpt4    = ProviderFactory.get_provider('openai')
gemini  = ProviderFactory.get_provider('gemini')
ollama  = ProviderFactory.get_provider('ollama')   # local, no API key needed
```

---

## LLM providers

`ProviderFactory.get_provider()` returns a cached singleton. `create_provider()` creates a fresh instance with explicit credentials.

**14 providers:**

| Provider | Models | Capabilities |
|----------|--------|--------------|
| Anthropic | Claude 3.x / 4.x | Chat, vision, batch (50% cost reduction) |
| OpenAI | GPT-4o, o1, o3, DALL-E | Chat, vision, image gen, embeddings, structured outputs |
| xAI | Grok-3, Aurora | Chat, vision, image gen |
| Mistral | Pixtral Large/12B | Chat, vision, embeddings |
| Cohere | Command-R | Chat, embeddings |
| Google Gemini | 2.0 Flash/Pro | Chat, vision, embeddings, search grounding |
| Perplexity | Sonar Pro | Chat, vision |
| Groq | Llama, Mixtral | Fast inference |
| HuggingFace | Stable Diffusion, vision models | Image gen, embeddings |
| Manus | Agent profiles | Chat, vision |
| ElevenLabs | TTS models | Text-to-speech |
| Ollama | Any local model (Llama, Llava, etc.) | Chat, vision, local inference |
| Gradient | DigitalOcean Gradient | Chat |
| ClaudeCode | Claude via CLI | Chat |

```python
from shared.llm_providers import ProviderFactory, Message

# Check what a provider supports before calling it
caps = ProviderFactory.get_capabilities('xai')
# {'chat': True, 'streaming': True, 'image_generation': True, 'vision': True, ...}

# Generate an image with xAI Aurora
provider = ProviderFactory.get_provider('xai')
image = provider.generate_image(prompt='A neon cityscape at midnight', model='aurora')

import base64
with open('output.png', 'wb') as f:
    f.write(base64.b64decode(image.image_data))

# Analyze an image with Claude
claude = ProviderFactory.get_provider('anthropic')
with open('photo.jpg', 'rb') as f:
    img_b64 = base64.b64encode(f.read()).decode()

analysis = claude.analyze_image(image=img_b64, prompt='What is in this image?')
print(analysis.content)
```

### Complexity router

Routes requests to cheap/balanced/expensive providers automatically based on task complexity:

```python
from shared.llm_providers import ProviderFactory, Message
from shared.llm_providers.complexity_router import ComplexityRouter

router = ComplexityRouter(
    providers={
        'simple':  ProviderFactory.get_provider('groq'),       # fast, cheap
        'medium':  ProviderFactory.get_provider('xai'),        # balanced
        'complex': ProviderFactory.get_provider('anthropic'),  # highest quality
    }
)

response = router.route_and_complete(
    task='Explain the Riemann hypothesis',
    messages=[Message(role='user', content='Explain the Riemann hypothesis')]
)
```

---

## Orchestration

Two patterns for multi-agent workflows.

### Dream Cascade — hierarchical research

Parallel workers → mid-tier synthesis → executive summary. Good for deep research and analysis tasks where you want layered reasoning.

```
8 Belter workers  →  2 Drummer synthesizers  →  1 Camina executive summary
```

```python
import asyncio
from shared.orchestration import DreamCascadeOrchestrator, DreamCascadeConfig
from shared.llm_providers import ProviderFactory

config = DreamCascadeConfig(
    belter_count=4,   # parallel workers
    drummer_count=2,  # mid-tier synthesizers
    camina_count=1,   # executive synthesizer
    primary_model='grok-3'
)

orchestrator = DreamCascadeOrchestrator(
    config=config,
    provider=ProviderFactory.get_provider('xai')
)

result = asyncio.run(
    orchestrator.execute_workflow('LLM safety research 2025')
)
print(result.result['summary'])
print(f"Cost: ${result.total_cost:.4f}")
print(f"Time: {result.execution_time:.1f}s")
```

Use different models per tier to control cost vs quality:

```python
config = DreamCascadeConfig(
    belter_model='llama3.2',           # local via Ollama for workers
    drummer_model='grok-3',            # balanced for mid synthesis
    camina_model='claude-sonnet-4-6'   # best model for final output
)
```

### Dream Swarm — parallel domain search

Spins up domain-specific agents in parallel. Good for broad information gathering across multiple sources.

```python
from shared.orchestration import DreamSwarmOrchestrator, DreamSwarmConfig

config = DreamSwarmConfig(
    num_agents=5,
    domains=['arxiv', 'github', 'news', 'wikipedia'],
    max_parallel=3
)

orchestrator = DreamSwarmOrchestrator(config, provider)
result = asyncio.run(orchestrator.execute_workflow('Latest advances in protein folding'))
```

### Custom orchestrators

Extend `BaseOrchestrator` and implement three methods:

```python
from shared.orchestration import BaseOrchestrator, SubTask, AgentResult
from typing import List

class MyOrchestrator(BaseOrchestrator):
    async def decompose_task(self, task: str, context: dict = None) -> List[SubTask]:
        return [
            SubTask(id='research', description=f'Research: {task}', agent_type='researcher', priority=1),
            SubTask(id='analyze',  description='Analyze findings',  agent_type='analyst',    priority=2),
        ]

    async def execute_subtask(self, subtask: SubTask, context: dict = None) -> AgentResult:
        response = self.provider.complete(
            messages=[{'role': 'user', 'content': subtask.description}]
        )
        return AgentResult(subtask_id=subtask.id, content=response.content, status='completed')

    async def synthesize_results(self, agent_results: List[AgentResult], context: dict = None) -> dict:
        combined  = '\n\n'.join(r.content for r in agent_results)
        synthesis = self.provider.complete(
            messages=[{'role': 'user', 'content': f'Synthesize:\n\n{combined}'}]
        )
        return {'summary': synthesis.content}
```

### Streaming progress events

```python
async def on_progress(event):
    print(f"[{event.event_type}] {event.message}")

orchestrator.stream_callback = on_progress
result = await orchestrator.execute_workflow(task)
```

---

## Data clients

18 structured API clients via `ClientFactory`:

```python
from shared.data_fetching import ClientFactory

# arXiv papers
arxiv  = ClientFactory.create_client('arxiv')
papers = arxiv.search(query='quantum error correction', max_results=10)

# GitHub repos
github = ClientFactory.create_client('github')
repos  = github.search_repositories('multi-agent LLM', sort='stars')

# Wikipedia
wiki    = ClientFactory.create_client('wikipedia')
article = wiki.get_article('Transformer (machine learning model)')

# PubMed
pubmed  = ClientFactory.create_client('pubmed')
studies = pubmed.search('CRISPR gene therapy 2024', max_results=20)

# Wolfram Alpha
wolfram = ClientFactory.create_client('wolfram')
answer  = wolfram.query('integrate x^2 from 0 to 1')
```

**All 18 clients:** arXiv, Semantic Scholar, Wikipedia, PubMed, GitHub, NASA, Census (ACS/SAIPE), NewsAPI, YouTube, OpenLibrary, Weather, Finance, FEC, Judiciary, Wolfram Alpha, Wayback Machine, MAL, Coze

---

## MCP server

Exposes all providers and data clients as MCP tools. Two transports:

```bash
# HTTP/SSE — port 5060 (for local Claude Desktop connections)
cd /path/to/geepers-kernel/mcp && python unified_server.py

# Remote HTTP — port 5061 (for Claude Desktop Custom Connectors)
cd /path/to/geepers-kernel/mcp/remote_mcp && python server.py
```

Tool naming follows the Dreamwalker convention:
- Data tools: `dream_of_arxiv`, `dream_of_github`, `dream_of_pubmed`, etc.
- Management tools: `dreamwalker_status`, `dreamwalker_cancel`, `dreamwalker_patterns`, etc.

---

## Flask web utilities

Drop-in Flask components for LLM-backed services:

```python
from flask import Flask
from shared.web import setup_cors, create_health_endpoint, LLMProxyBlueprint

app = Flask(__name__)
setup_cors(app)
create_health_endpoint(app)  # adds GET /health

# Drop-in multi-provider LLM proxy
proxy = LLMProxyBlueprint(name='api')
app.register_blueprint(proxy.blueprint, url_prefix='/api')

# Routes added:
# POST /api/complete   — chat completion
# POST /api/stream     — streaming completion (SSE)
# POST /api/vision     — image analysis
# GET  /api/models     — list available models
```

**Bearer token auth:**

```python
from shared.web.auth import require_api_token

@app.route('/protected')
@require_api_token(['your-token-here'])
def protected():
    return {'message': 'authenticated'}
```

**Rate limiting:**

```python
from shared.web import RateLimiter

limiter = RateLimiter(calls=100, period=60, by_ip=True)

@app.before_request
def check_rate():
    if not limiter.check_limit(request.remote_addr):
        return {'error': 'rate limit exceeded'}, 429
```

---

## Cost tracking

Tracks token usage and calculates costs. Pricing data in `observability/pricing.yaml` covers 8 providers (OpenAI, Anthropic, xAI, Mistral, Cohere, Gemini, Perplexity, Groq) with per-1M-token rates.

```python
from shared.observability import get_cost_tracker

tracker = get_cost_tracker()

# Calculate cost for a call without tracking it
cost = tracker.calculate_cost(
    provider='openai',
    model='gpt-4o',
    prompt_tokens=1000,
    completion_tokens=500
)
print(f"${cost:.4f}")  # $0.0075

# Track all calls for the session
tracker.track_cost(provider='xai', model='grok-3', prompt_tokens=800, completion_tokens=200)

# See where your budget is going
breakdown = tracker.get_cost_breakdown()
for provider, cost in breakdown.by_provider.items():
    print(f"{provider}: ${cost:.4f}")

# Set a daily budget
tracker.set_budget(amount=10.00, period='daily')
if tracker.is_over_budget():
    print("Daily budget exceeded")
```

---

## Exception hierarchy

Catch `GeepersError` to handle any library error. Catch specific subclasses for fine-grained handling.

```python
from shared.exceptions import (
    GeepersError,
    # Provider errors
    ProviderError, RateLimitError, AuthenticationError,
    ProviderUnavailableError, ModelNotFoundError,
    # Orchestration errors
    OrchestrationError, SubtaskError, WorkflowTimeoutError,
    # Data errors
    DataFetchingError, DataSourceUnavailableError,
    # Config errors
    ConfigurationError, MissingApiKeyError,
)

try:
    response = provider.complete(messages=[...])
except RateLimitError as e:
    print(f"Rate limited by {e.provider}. Retry after {e.retry_after}s")
except AuthenticationError as e:
    print(f"Bad API key for {e.provider}")
except ProviderUnavailableError:
    # fall back to a different provider
    ...
except GeepersError as e:
    # catch-all for anything the library raises
    print(f"Library error: {e}")
```

---

## Configuration

API keys load from `~/.env`, environment variables, or a project-local `.env`. Precedence: defaults < config file < `.env` < environment variables.

```python
from shared.config import ConfigManager

config = ConfigManager(app_name='myapp')
key = config.get_api_key('xai')  # reads XAI_API_KEY
```

Environment variables: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`

---

## Utilities

```python
from shared.utils import vision, embeddings
from shared.utils.text_utils import truncate, chunk_text
from shared.utils.retry import retry_async
from shared.document_generation import PDFGenerator, DOCXGenerator, MarkdownGenerator

# Generate a PDF from orchestrator output
pdf = PDFGenerator()
pdf.write('report.pdf', title='Research Summary', content=result.result['summary'])

# Retry with exponential backoff
@retry_async(max_retries=3, base_delay=1.0)
async def unstable_call():
    return await api.fetch()
```

Included: vision helpers, embeddings, PDF/DOCX/Markdown generation, TTS, multi-search, citation formatting, async adapters, document parsers, observability hooks.

---

## Tests

```bash
pytest                               # all 17 test files
pytest tests/test_providers.py -v   # single file
pytest -v -k "test_anthropic"        # filter by name
pytest --cov=. --cov-report=html     # coverage report
```

---

## Development install

```bash
git clone https://github.com/lukeslp/geepers-kernel
cd geepers-kernel
pip install -e .[all]

# Formatting
black . && isort .
```

---

## Project layout

```
geepers-kernel/
├── llm_providers/        # 14 providers + factory + complexity router
├── orchestration/        # Dream Cascade, Dream Swarm, base classes, patterns
├── data_fetching/        # 18 API clients + factory
├── mcp/                  # MCP server (unified HTTP/SSE, stdio, remote)
├── remote_mcp/           # FastMCP wrapper for Claude Desktop Custom Connectors
├── web/                  # Flask blueprints, auth, CORS, health, proxy
├── tools/                # Tool registry (MCP-compatible schemas)
├── document_generation/  # PDF, DOCX, Markdown generators
├── utils/                # Vision, embeddings, retry, text, async, TTS
├── observability/        # Cost tracking, metrics, pricing.yaml
├── memory/               # Redis caching
├── exceptions.py         # GeepersError hierarchy
├── config.py             # ConfigManager
└── naming.py             # Canonical names + legacy aliases
```

Each module has its own `CLAUDE.md` with detailed API docs and usage examples.

---

## Author

**Luke Steuber**
[lukesteuber.com](https://lukesteuber.com) · [@lukesteuber.com](https://bsky.app/profile/lukesteuber.com) on Bluesky

MIT License · [github.com/lukeslp/geepers-kernel](https://github.com/lukeslp/geepers-kernel)
