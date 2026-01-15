# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module: tools

Tool registry system for dynamic module loading and management. Provides centralized registration, discovery, and execution of tools for MCP servers and orchestrators.

### Overview

The tools module provides:
- **ToolRegistry** - Singleton registry for tool registration and lookup
- **ToolModuleBase** - Base class for creating tool modules
- **DataToolModuleBase** - Specialized base for data fetching tools
- Provider-specific tool modules (OpenAI, Anthropic, xAI, etc.)
- Data source tool modules (Arxiv, GitHub, NASA, etc.)

### ToolRegistry

Centralized tool management with singleton pattern:

```python
from tools import ToolRegistry, get_registry

# Get singleton instance
registry = get_registry()  # or ToolRegistry.get_instance()

# Register a tool
registry.register_tool(
    name='search',
    schema={
        'name': 'search',
        'description': 'Search for information',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string'},
                'limit': {'type': 'integer', 'default': 10}
            },
            'required': ['query']
        }
    },
    handler=search_handler,
    module_name='search_module'
)

# Get all tools
all_tools = registry.get_all_tools()

# Get enabled tools only
enabled_tools = registry.get_enabled_tools()

# Execute tool
result = await registry.call_tool('search', {'query': 'test', 'limit': 5})
```

### ToolModuleBase

Base class for creating custom tool modules:

```python
from tools import ToolModuleBase

class MyToolModule(ToolModuleBase):
    """Custom tool module"""

    def __init__(self):
        super().__init__(
            module_name='my_tools',
            version='1.0.0'
        )

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tool schemas"""
        return [
            {
                'name': 'my_tool',
                'description': 'Does something useful',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'param': {'type': 'string'}
                    }
                }
            }
        ]

    async def call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute tool"""
        if tool_name == 'my_tool':
            return await self.my_tool(arguments['param'])

    async def my_tool(self, param: str):
        """Tool implementation"""
        return f"Result for {param}"

# Register module
module = MyToolModule()
registry = get_registry()
registry.register_module('my_tools', module)
module.register_with_registry(registry)
```

### DataToolModuleBase

Specialized base class for data fetching tools:

```python
from tools import DataToolModuleBase
from data_fetching import ArxivClient

class ArxivToolModule(DataToolModuleBase):
    """Arxiv data tool"""

    def __init__(self):
        super().__init__(
            module_name='arxiv',
            client_class=ArxivClient,
            version='1.0.0'
        )

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'arxiv_search',
                'description': 'Search academic papers on arXiv',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'query': {'type': 'string'},
                        'max_results': {'type': 'integer', 'default': 10}
                    }
                }
            }
        ]

    async def call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if tool_name == 'arxiv_search':
            papers = self.client.search(
                query=arguments['query'],
                max_results=arguments.get('max_results', 10)
            )
            return [self.format_paper(p) for p in papers]

    def format_paper(self, paper):
        return {
            'title': paper.title,
            'authors': paper.authors,
            'abstract': paper.abstract,
            'url': paper.pdf_url
        }
```

### Provider Tools

Tools for LLM provider capabilities:

#### OpenAI Tools

```python
from tools import openai_tools

# Available tools:
# - openai_complete: Chat completion
# - openai_stream: Streaming completion
# - openai_generate_image: DALL-E image generation
# - openai_analyze_image: GPT-4V vision analysis
# - openai_embed: Text embeddings

registry = get_registry()

# Call OpenAI tool
result = await registry.call_tool('openai_complete', {
    'messages': [{'role': 'user', 'content': 'Hello'}],
    'model': 'gpt-4',
    'temperature': 0.7
})
```

#### Anthropic Tools

```python
# Available tools:
# - anthropic_complete: Claude completion
# - anthropic_stream: Streaming completion
# - anthropic_analyze_image: Claude vision analysis

result = await registry.call_tool('anthropic_complete', {
    'messages': [{'role': 'user', 'content': 'Explain quantum computing'}],
    'model': 'claude-3.5-sonnet',
    'max_tokens': 1000
})
```

#### xAI Tools

```python
# Available tools:
# - xai_complete: Grok completion
# - xai_stream: Streaming completion
# - xai_generate_image: Aurora image generation
# - xai_analyze_image: Grok vision analysis

result = await registry.call_tool('xai_generate_image', {
    'prompt': 'A futuristic city',
    'model': 'aurora',
    'size': '1024x1024'
})
```

### Data Source Tools

Tools for external data sources:

```python
# Arxiv
papers = await registry.call_tool('arxiv_search', {
    'query': 'quantum computing',
    'max_results': 10
})

# GitHub
repos = await registry.call_tool('github_search', {
    'query': 'machine learning',
    'language': 'python'
})

# NASA
apod = await registry.call_tool('nasa_apod', {
    'date': '2024-01-01'
})

# Wikipedia
article = await registry.call_tool('wikipedia_search', {
    'query': 'Quantum computing'
})

# News
articles = await registry.call_tool('news_search', {
    'query': 'artificial intelligence',
    'category': 'technology'
})

# Weather
weather = await registry.call_tool('weather_current', {
    'city': 'San Francisco',
    'country': 'US'
})
```

### Module Management

```python
registry = get_registry()

# Enable/disable modules
registry.enable_module('arxiv', enabled=True)
registry.enable_module('github', enabled=False)

# Check module status
is_enabled = registry.is_module_enabled('arxiv')

# Get module config
config = registry.get_module_config('arxiv')

# Update module config
registry.update_module_config('arxiv', {
    'max_results': 20,
    'cache_ttl': 3600
})

# List all modules
modules = registry.list_modules()
```

### Tool Discovery

Automatic tool discovery from packages:

```python
from tools import ToolRegistry

registry = ToolRegistry.get_instance()

# Discover tools from package
registry.discover_tools_from_package('tools')

# Get discovered tools
tools = registry.get_all_tools()
print(f"Discovered {len(tools)} tools")
```

### Registering Provider Tools

```python
from tools import register_provider_tools

# Register all provider tools
register_provider_tools(registry)

# Now available:
# - openai_complete, openai_generate_image, openai_analyze_image
# - anthropic_complete, anthropic_analyze_image
# - xai_complete, xai_generate_image, xai_analyze_image
# - gemini_complete, gemini_analyze_image
# - mistral_complete, cohere_complete
# - etc.
```

### Registering Data Tools

```python
from tools import register_data_tools, get_data_tool_status

# Register all data source tools
register_data_tools(registry)

# Check status
status = get_data_tool_status()
for tool, info in status.items():
    print(f"{tool}: {'✓' if info['available'] else '✗'}")
```

### Tool Schema Format

Tools follow MCP tool schema:

```python
tool_schema = {
    'name': 'tool_name',
    'description': 'What the tool does',
    'inputSchema': {
        'type': 'object',
        'properties': {
            'param1': {
                'type': 'string',
                'description': 'First parameter'
            },
            'param2': {
                'type': 'integer',
                'default': 10,
                'description': 'Second parameter'
            }
        },
        'required': ['param1']
    }
}
```

### Handler Functions

Tool handlers can be sync or async:

```python
# Synchronous handler
def sync_handler(arguments: Dict[str, Any]) -> Any:
    return {'result': 'done'}

# Asynchronous handler
async def async_handler(arguments: Dict[str, Any]) -> Any:
    await some_async_operation()
    return {'result': 'done'}

# Register
registry.register_tool(
    name='my_tool',
    schema=schema,
    handler=async_handler
)
```

### Error Handling

```python
from tools import ToolRegistry

registry = get_registry()

try:
    result = await registry.call_tool('some_tool', {'param': 'value'})
except KeyError:
    print("Tool not found")
except ValueError as e:
    print(f"Invalid arguments: {e}")
except Exception as e:
    print(f"Tool execution failed: {e}")
```

### Testing

```python
import pytest
from tools import ToolRegistry

@pytest.fixture
def registry():
    """Fresh registry for each test"""
    ToolRegistry.reset_instance()
    return ToolRegistry.get_instance()

def test_tool_registration(registry):
    def handler(args):
        return {'result': args['value'] * 2}

    registry.register_tool(
        name='double',
        schema={
            'name': 'double',
            'inputSchema': {
                'type': 'object',
                'properties': {'value': {'type': 'number'}}
            }
        },
        handler=handler
    )

    result = registry.call_tool('double', {'value': 5})
    assert result['result'] == 10

@pytest.mark.asyncio
async def test_async_tool(registry):
    async def async_handler(args):
        return {'async_result': True}

    registry.register_tool(
        name='async_tool',
        schema={'name': 'async_tool', 'inputSchema': {'type': 'object'}},
        handler=async_handler
    )

    result = await registry.call_tool('async_tool', {})
    assert result['async_result'] is True
```

### Files in This Module

- `registry.py` - ToolRegistry singleton
- `module_base.py` - ToolModuleBase abstract class
- `data_tool_base.py` - DataToolModuleBase for data sources
- `provider_registry.py` - Register all provider tools
- `data_registry.py` - Register all data tools
- `anthropic_tools.py` - Anthropic (Claude) tools
- `openai_tools.py` - OpenAI (GPT, DALL-E) tools
- `xai_tools.py` - xAI (Grok, Aurora) tools
- `gemini_tools.py` - Google Gemini tools
- `mistral_tools.py` - Mistral tools
- `cohere_tools.py` - Cohere tools
- `groq_tools.py` - Groq tools
- `huggingface_tools.py` - HuggingFace tools
- `arxiv_tool.py` - Arxiv academic papers
- `github_tool.py` - GitHub repositories
- `nasa_tool.py` - NASA space data
- `news_tool.py` - News articles
- `wikipedia_tool.py` - Wikipedia articles
- `weather_tool.py` - Weather data
- `gradient_tools.py` - DigitalOcean Gradient AI (Knowledge Bases, Agents)
- And 10+ more data source tools

### Gradient AI Tools

Tools for DigitalOcean Gradient AI Platform features:

```python
from tools import GradientToolModule, register_gradient_tools, get_registry

# Register Gradient tools
registry = get_registry()
register_gradient_tools(registry)

# Or register module directly
module = GradientToolModule()
module.register_with_registry(registry)

# Available tools:
# - gradient_query_kb: Query Knowledge Base with RAG citations
# - gradient_agent_chat: Chat with configured AI Agents
# - gradient_list_knowledge_bases: List available KBs
# - gradient_list_agents: List available Agents
# - gradient_complete: Serverless LLM completion
# - gradient_list_models: List available models

# Query a Knowledge Base
kb_result = await registry.call_tool('gradient_query_kb', {
    'kb_id': 'uuid-of-knowledge-base',
    'query': 'What is the return policy?',
    'num_results': 5
})
# Returns: {'success': True, 'results': [...], 'citations': [...]}

# Chat with an Agent
agent_result = await registry.call_tool('gradient_agent_chat', {
    'agent_id': 'uuid-of-agent',
    'message': 'Help me understand this document'
})

# List resources
kbs = await registry.call_tool('gradient_list_knowledge_bases', {})
agents = await registry.call_tool('gradient_list_agents', {})
models = await registry.call_tool('gradient_list_models', {})
```

Requires `GRADIENT_API_KEY` environment variable or `do-gradient-ai` package.

### Integration with MCP Server

```python
from mcp.unified_server import UnifiedMCPServer
from tools import get_registry, register_provider_tools, register_data_tools, register_gradient_tools

# Setup registry
registry = get_registry()
register_provider_tools(registry)
register_data_tools(registry)
register_gradient_tools(registry)  # Add Gradient AI tools

# MCP server uses registry to expose tools
server = UnifiedMCPServer(tool_registry=registry)
```

### Best Practices

- Use singleton registry (`get_registry()`) for global access
- Implement proper error handling in tool handlers
- Validate arguments before execution
- Use async handlers for I/O operations
- Enable only needed modules to reduce overhead
- Document tool schemas thoroughly
- Test tools with mock data before production
- Cache expensive operations when appropriate
- Log tool executions for debugging
- Use type hints in handler functions

### Common Patterns

#### Conditional Tool Loading
```python
registry = get_registry()

# Load only specific tools
if 'OPENAI_API_KEY' in os.environ:
    register_openai_tools(registry)

if 'ANTHROPIC_API_KEY' in os.environ:
    register_anthropic_tools(registry)
```

#### Tool Chaining
```python
# Use one tool's output as input to another
papers = await registry.call_tool('arxiv_search', {'query': 'AI'})
summaries = []
for paper in papers[:3]:
    summary = await registry.call_tool('anthropic_complete', {
        'messages': [{'role': 'user', 'content': f'Summarize: {paper["abstract"]}'}]
    })
    summaries.append(summary)
```

#### Custom Tool Wrapper
```python
class ToolExecutor:
    def __init__(self):
        self.registry = get_registry()

    async def execute_with_retry(self, tool_name, arguments, max_retries=3):
        for attempt in range(max_retries):
            try:
                return await self.registry.call_tool(tool_name, arguments)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
```

### Dependencies

- `llm_providers/` - For provider tools
- `data_fetching/` - For data source tools
- Standard library: `typing`, `importlib`, `inspect`
