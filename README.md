# geepers-kernel

[![PyPI](https://img.shields.io/pypi/v/geepers-kernel.svg)](https://pypi.org/project/geepers-kernel/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Core infrastructure for the [geepers](https://github.com/lukeslp/geepers) 72-agent system. Provides a unified interface to 14 LLM providers, two multi-agent orchestration patterns, 18 data clients, an MCP server, and Flask web utilities — all from a single `pip install`.

Previously published as `geepers-core` and `dr-eamer-ai-shared`. Live at [dr.eamer.dev](https://dr.eamer.dev).

---

## Install

```bash
# All providers
pip install geepers-kernel[all]

# Specific providers only
pip install geepers-kernel[anthropic,xai]

# Core only (no provider SDKs)
pip install geepers-kernel
```

Optional extras: `anthropic`, `openai`, `xai`, `mistral`, `cohere`, `gemini`, `perplexity`, `groq`, `huggingface`, `redis`, `telemetry`

---

## Quick start

```python
from llm_providers import ProviderFactory, Message

# Chat with Grok-3
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
# Switch providers with the same interface
claude = ProviderFactory.get_provider('anthropic')
gpt4 = ProviderFactory.get_provider('openai')
gemini = ProviderFactory.get_provider('gemini')
ollama = ProviderFactory.get_provider('ollama')  # local, no API key needed
```

---

## LLM Providers

`ProviderFactory` returns a cached singleton per provider. `create_provider()` returns a fresh instance with explicit credentials.

**14 providers:**

| Provider | Models | Extras |
|----------|--------|--------|
| Anthropic | Claude 3.5/4.x | Vision |
| OpenAI | GPT-4o, o1, DALL-E | Vision, image gen, embeddings |
| xAI | Grok-3, Aurora | Vision, image gen |
| Mistral | Pixtral Large/12B | Vision, embeddings |
| Cohere | Command-R | Embeddings |
| Google Gemini | 2.0 Flash/Pro | Vision, embeddings, search grounding |
| Perplexity | Sonar Pro | Vision |
| Groq | Llama, Mixtral | Fast inference |
| HuggingFace | Stable Diffusion, vision | Image gen, embeddings |
| Manus | Agent profiles | Vision |
| ElevenLabs | TTS models | Text-to-speech |
| Ollama | Llama, Llava, any local model | Local inference, vision |
| Gradient | DigitalOcean Gradient | Chat |
| ClaudeCode | Claude via CLI | Chat |

```python
from llm_providers import ProviderFactory, Message, PROVIDER_CAPABILITIES

# Check what a provider can do before calling it
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

Routes requests to cheap/balanced/expensive providers automatically:

```python
from llm_providers import ProviderFactory
from llm_providers.complexity_router import ComplexityRouter

router = ComplexityRouter(
    providers={
        'simple': ProviderFactory.get_provider('groq'),      # fast, cheap
        'medium': ProviderFactory.get_provider('xai'),       # balanced
        'complex': ProviderFactory.get_provider('anthropic') # highest quality
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

8 parallel workers → mid-tier synthesis → executive summary. Good for deep research and analysis tasks.

```python
import asyncio
from orchestration import DreamCascadeOrchestrator, DreamCascadeConfig
from llm_providers import ProviderFactory

config = DreamCascadeConfig(
    belter_count=4,    # parallel workers
    drummer_count=2,   # mid-tier synthesizers
    camina_count=1,    # executive synthesizer
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

Use different models per tier to cut costs:

```python
config = DreamCascadeConfig(
    belter_model='llama3.2',      # local via Ollama for workers
    drummer_model='grok-3',       # balanced for mid synthesis
    camina_model='claude-sonnet-4-5'  # best model for final output
)
```

### Dream Swarm — parallel domain search

Spins up domain-specific agents in parallel. Good for broad information gathering across multiple sources.

```python
from orchestration import DreamSwarmOrchestrator, DreamSwarmConfig

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
from orchestration import BaseOrchestrator, OrchestratorConfig, SubTask, AgentResult
from typing import List

class MyOrchestrator(BaseOrchestrator):
    async def decompose_task(self, task: str, context: dict = None) -> List[SubTask]:
        return [
            SubTask(id='research', description=f'Research: {task}', agent_type='researcher', priority=1),
            SubTask(id='analyze', description='Analyze findings', agent_type='analyst', priority=2),
        ]

    async def execute_subtask(self, subtask: SubTask, context: dict = None) -> AgentResult:
        response = self.provider.complete(
            messages=[{'role': 'user', 'content': subtask.description}]
        )
        return AgentResult(subtask_id=subtask.id, content=response.content, status='completed')

    async def synthesize_results(self, agent_results: List[AgentResult], context: dict = None) -> dict:
        combined = '\n\n'.join(r.content for r in agent_results)
        synthesis = self.provider.complete(
            messages=[{'role': 'user', 'content': f'Synthesize:\n\n{combined}'}]
        )
        return {'summary': synthesis.content}
```

### Streaming progress

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
from data_fetching import ClientFactory

# arXiv papers
arxiv = ClientFactory.create_client('arxiv')
papers = arxiv.search(query='quantum error correction', max_results=10)

# GitHub repos
github = ClientFactory.create_client('github')
repos = github.search_repositories('multi-agent LLM', sort='stars')

# Wikipedia
wiki = ClientFactory.create_client('wikipedia')
article = wiki.get_article('Transformer (machine learning model)')

# PubMed
pubmed = ClientFactory.create_client('pubmed')
studies = pubmed.search('CRISPR gene therapy 2024', max_results=20)
```

**All 18 clients:** arXiv, Semantic Scholar, Wikipedia, PubMed, GitHub, NASA, Census ACS/SAIPE, NewsAPI, YouTube, OpenLibrary, Weather, Finance, FEC, Judiciary, Wolfram Alpha, Wayback Machine

---

## MCP server

Exposes all providers and data clients as MCP tools. Runs on two transports:

```bash
# HTTP/SSE on port 5060 (for local Claude Desktop connections)
cd /home/coolhand/shared/mcp && python unified_server.py

# Or via service manager
sm start mcp-orchestrator
```

- Port **5060** — HTTP/SSE transport
- Port **5061** — Remote HTTP for Claude Desktop Custom Connectors

Tool naming follows the Dreamwalker convention: data tools are `dream_of_arxiv`, `dream_of_github`, etc. Management tools are `dreamwalker_status`, `dreamwalker_cancel`, etc.

---

## Web utilities

Reusable Flask components for building LLM-backed services:

```python
from flask import Flask
from web import setup_cors, create_health_endpoint, LLMProxyBlueprint
from llm_providers import ProviderFactory

app = Flask(__name__)
setup_cors(app)
create_health_endpoint(app)

# Drop-in multi-provider LLM proxy
proxy = LLMProxyBlueprint(name='api')
app.register_blueprint(proxy.blueprint, url_prefix='/api')

# Provides:
# POST /api/complete   — chat completion
# POST /api/stream     — streaming completion
# POST /api/vision     — image analysis
# GET  /api/models     — list models
```

**Auth:**

```python
from web.auth import require_api_token

@app.route('/protected')
@require_api_token(['your-token-here'])
def protected():
    return {'message': 'authenticated'}
```

**Rate limiting:**

```python
from web import RateLimiter

limiter = RateLimiter(calls=100, period=60, by_ip=True)

@app.before_request
def check_rate():
    if not limiter.check_limit(request.remote_addr):
        return {'error': 'rate limit exceeded'}, 429
```

---

## Configuration

API keys load from `~/.env`, environment variables, or `/home/coolhand/documentation/API_KEYS.md`. Precedence: defaults < config file < `.env` < environment variables.

```python
from config import ConfigManager

config = ConfigManager(app_name='myapp')
key = config.get_api_key('xai')  # reads XAI_API_KEY
```

Key environment variables: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`

---

## Utilities

```python
from utils import vision, embeddings
from utils.text_utils import truncate, chunk_text
from utils.retry import retry_async
from document_generation import PDFGenerator, DOCXGenerator, MarkdownGenerator

# Generate a PDF from orchestrator output
pdf = PDFGenerator()
pdf.write('report.pdf', title='Research Summary', content=result.result['summary'])

# Retry with exponential backoff
@retry_async(max_retries=3, base_delay=1.0)
async def unstable_call():
    return await api.fetch()
```

**Included:** vision helpers, embeddings, PDF/DOCX/Markdown generation, TTS, multi-search, citation formatting, async adapters, document parsers, cost tracking, observability hooks

---

## Tests

```bash
pytest                              # all 17 test files
pytest tests/test_providers.py -v  # single file
pytest -v -k "test_anthropic"      # filter by name
pytest --cov=. --cov-report=html   # coverage report
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
├── llm_providers/       # 14 providers + factory + complexity router
├── orchestration/       # Dream Cascade, Dream Swarm, base classes, patterns
├── data_fetching/       # 18 API clients + factory
├── mcp/                 # MCP server (unified, stdio, streaming)
├── web/                 # Flask blueprints, auth, CORS, health, proxy
├── tools/               # Tool registry (MCP-compatible schemas)
├── document_generation/ # PDF, DOCX, Markdown generators
├── utils/               # Vision, embeddings, retry, text, async, TTS
├── observability/       # Cost tracking, metrics
├── memory/              # Redis caching
├── config.py            # ConfigManager
└── naming.py            # Canonical names + legacy aliases
```

Each module has its own `CLAUDE.md` with detailed API docs and code examples.

---

## Author

**Luke Steuber**
[lukesteuber.com](https://lukesteuber.com) · [@lukesteuber.com](https://bsky.app/profile/lukesteuber.com) on Bluesky

MIT License · [github.com/lukeslp/geepers-kernel](https://github.com/lukeslp/geepers-kernel)
