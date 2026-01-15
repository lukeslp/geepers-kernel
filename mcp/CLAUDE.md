# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module: mcp

Model Context Protocol (MCP) server implementation exposing orchestrator agents, tools, and data sources via HTTP/SSE endpoints. Runs on port 5060.

### Overview

The MCP server provides:
- Unified orchestrator tools for long-running workflows
- Tool registry for dynamic tool discovery
- Server-Sent Events (SSE) streaming for progress updates
- State management for active workflows
- Multiple MCP server implementations

### Main Server: unified_server.py

Entry point for the comprehensive MCP server (port 5060).

**Start server:**
```bash
cd /home/coolhand/shared/mcp
python unified_server.py
```

**Or via service manager:**
```bash
/home/coolhand/service_manager.py start mcp-orchestrator
/home/coolhand/service_manager.py status
```

### MCP Tools Provided

#### dream_research - Dream Cascade Workflow

Hierarchical research with 3-tier agent system:

```python
# Tool call
{
  "name": "dream_research",
  "arguments": {
    "task": "Research quantum computing applications in cryptography",
    "belter_count": 3,      # Tier 1 agents
    "drummer_count": 2,     # Tier 2 agents
    "camina_count": 1,      # Tier 3 agents
    "provider": "xai",
    "model": "grok-3",
    "stream": true,         # Enable SSE streaming
    "webhook_url": "https://example.com/webhook"  # Optional
  }
}

# Response
{
  "task_id": "workflow-abc123",
  "status": "running",
  "stream_url": "/stream/workflow-abc123",
  "message": "Workflow started successfully"
}
```

#### dream_search - Dream Swarm Workflow

Multi-domain parallel search:

```python
# Tool call
{
  "name": "dream_search",
  "arguments": {
    "task": "Find latest AI safety research",
    "num_agents": 5,
    "domains": ["arxiv", "github", "news", "wikipedia"],
    "max_parallel": 3,
    "provider": "xai",
    "stream": true
  }
}
```

#### dreamwalker_status - Check Workflow Status

```python
# Tool call
{
  "name": "dreamwalker_status",
  "arguments": {
    "task_id": "workflow-abc123"
  }
}

# Response
{
  "task_id": "workflow-abc123",
  "status": "running",        # or "completed", "failed", "cancelled"
  "progress": 45,             # Percentage
  "started_at": "2024-01-01T12:00:00Z",
  "agent_results": [...],
  "current_stage": "synthesis"
}
```

#### dreamwalker_cancel - Cancel Running Workflow

```python
# Tool call
{
  "name": "dreamwalker_cancel",
  "arguments": {
    "task_id": "workflow-abc123"
  }
}

# Response
{
  "success": true,
  "message": "Workflow cancelled",
  "task_id": "workflow-abc123"
}
```

#### dreamwalker_patterns - List Orchestrator Patterns

```python
# Tool call
{
  "name": "dreamwalker_patterns"
}

# Response
{
  "patterns": [
    {
      "name": "dream_cascade",
      "description": "Hierarchical research with 3-tier agents",
      "config_options": {
        "belter_count": "integer (1-10)",
        "drummer_count": "integer (1-5)",
        "camina_count": "integer (1-3)"
      }
    },
    {
      "name": "dream_swarm",
      "description": "Multi-domain parallel search",
      "config_options": {
        "num_agents": "integer (1-20)",
        "domains": "list of strings",
        "max_parallel": "integer (1-10)"
      }
    }
  ]
}
```

#### dreamwalker_list_tools - List All Registered Tools

```python
# Tool call
{
  "name": "dreamwalker_list_tools",
  "arguments": {
    "category": "data"  # Optional: filter by category
  }
}

# Response
{
  "tools": [
    {
      "name": "arxiv_search",
      "description": "Search academic papers on arXiv",
      "category": "data",
      "parameters": {...}
    },
    ...
  ]
}
```

#### dreamwalker_execute_tool - Execute Registered Tool

```python
# Tool call
{
  "name": "dreamwalker_execute_tool",
  "arguments": {
    "tool_name": "arxiv_search",
    "tool_args": {
      "query": "quantum computing",
      "max_results": 10
    }
  }
}

# Response
{
  "success": true,
  "result": [...],
  "execution_time": 1.234
}
```

### MCP Resources

#### orchestrator://{pattern}/info

Get orchestrator pattern metadata:

```
GET orchestrator://dream_cascade/info

Response:
{
  "name": "dream_cascade",
  "description": "Hierarchical research orchestrator",
  "agent_tiers": ["belter", "drummer", "camina"],
  "config_schema": {...}
}
```

#### orchestrator://{task_id}/status

Get workflow status:

```
GET orchestrator://workflow-abc123/status

Response:
{
  "task_id": "workflow-abc123",
  "status": "running",
  "progress": 60,
  "agent_results": [...],
  "metadata": {...}
}
```

#### orchestrator://{task_id}/results

Get workflow results:

```
GET orchestrator://workflow-abc123/results

Response:
{
  "task_id": "workflow-abc123",
  "status": "completed",
  "result": {
    "summary": "...",
    "details": [...]
  },
  "total_cost": 0.05,
  "execution_time": 45.2,
  "agent_results": [...]
}
```

### Streaming via SSE

Server-Sent Events for real-time progress updates:

```bash
# Subscribe to workflow stream
curl -N http://localhost:5060/stream/workflow-abc123

# Events received:
event: task_started
data: {"task_id": "workflow-abc123", "message": "Starting workflow"}

event: subtask_created
data: {"subtask_id": "task-1", "description": "Research topic"}

event: subtask_completed
data: {"subtask_id": "task-1", "status": "completed", "progress": 33}

event: synthesis_started
data: {"message": "Synthesizing results"}

event: task_completed
data: {"task_id": "workflow-abc123", "status": "completed", "result": {...}}
```

### State Management

The server maintains workflow state:

```python
from mcp.unified_server import WorkflowState

state = WorkflowState()

# Create workflow
workflow_info = state.create_workflow(
    task_id='workflow-123',
    orchestrator_type='dream_cascade',
    task='Research topic',
    config=config
)

# Update status
state.update_workflow(task_id='workflow-123', status='running')

# Get status
info = state.get_workflow('workflow-123')

# Clean up completed
state.cleanup_completed(max_retain=100)
```

### Other MCP Servers

#### providers_server.py

Exposes LLM provider tools:
- `llm_complete` - Chat completion
- `llm_stream` - Streaming completion
- `llm_vision` - Image analysis
- `llm_image_gen` - Image generation

#### data_server.py

Exposes data fetching tools:
- `arxiv_search`
- `github_search`
- `news_search`
- `wikipedia_search`
- And 10+ more data sources

#### cache_server.py

Response caching layer:
- `cache_get` - Retrieve cached response
- `cache_set` - Store response
- `cache_invalidate` - Clear cache

#### utility_server.py

General utility tools:
- `text_process` - Text processing
- `embed_text` - Generate embeddings
- `parse_document` - Document parsing

#### config_server.py

Configuration management:
- `config_get` - Get config value
- `config_set` - Set config value
- `config_list` - List all config

### Tool Registry

Dynamic tool discovery and registration:

```python
from mcp.tool_registry import ToolRegistry, get_tool_registry

registry = get_tool_registry()

# Register tool
registry.register_tool(
    name='my_tool',
    schema={
        'name': 'my_tool',
        'description': 'Does something useful',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'param': {'type': 'string'}
            }
        }
    },
    handler=my_handler_function,
    module_name='my_module'
)

# Get all tools
tools = registry.get_all_tools()

# Execute tool
result = await registry.call_tool('my_tool', {'param': 'value'})
```

### Streaming Bridge

SSE streaming infrastructure:

```python
from mcp.streaming import StreamingBridge, get_streaming_bridge

bridge = get_streaming_bridge()

# Register stream
bridge.register_stream('task-123')

# Send event
bridge.send_event(
    task_id='task-123',
    event_type='progress',
    data={'progress': 50, 'message': 'Halfway done'}
)

# Subscribe (in separate coroutine/thread)
async for event in bridge.subscribe('task-123'):
    print(event)

# Cleanup
bridge.unregister_stream('task-123')
```

### Background Loop

Execute long-running workflows in background:

```python
from mcp.background_loop import submit_background_task

async def long_workflow():
    # Do work
    result = await orchestrator.execute_workflow(task)
    return result

# Submit to background loop
task_id = submit_background_task(long_workflow())
```

### Installation

```bash
cd /home/coolhand/shared/mcp

# Install dependencies
pip install -r requirements.txt

# Start server
python unified_server.py

# Or via service manager
/home/coolhand/service_manager.py start mcp-orchestrator
```

### Configuration

Configure via `/home/coolhand/shared/mcp/config.json`:

```json
{
  "port": 5060,
  "host": "0.0.0.0",
  "default_provider": "xai",
  "max_workflows": 50,
  "log_level": "INFO",
  "enable_cors": true,
  "webhook_timeout": 30
}
```

Or via environment variables:
```bash
export MCP_PORT=5060
export MCP_DEFAULT_PROVIDER=xai
```

### Testing

```python
import pytest
from mcp.unified_server import WorkflowState

@pytest.mark.asyncio
async def test_workflow_creation():
    state = WorkflowState()
    workflow = state.create_workflow(
        task_id='test-1',
        orchestrator_type='dream_cascade',
        task='Test',
        config=OrchestratorConfig()
    )
    assert workflow['task_id'] == 'test-1'
    assert workflow['status'] == 'pending'
```

### Files in This Module

- `unified_server.py` - Main MCP server (port 5060)
- `providers_server.py` - LLM provider tools
- `data_server.py` - Data fetching tools
- `cache_server.py` - Caching layer
- `utility_server.py` - Utility tools
- `config_server.py` - Configuration tools
- `tool_registry.py` - Tool registration and discovery
- `tool_metadata.py` - Tool schema definitions
- `streaming.py` - SSE streaming infrastructure
- `streaming_endpoint.py` - SSE endpoint handlers
- `background_loop.py` - Background task executor
- `app.py` - Flask app setup
- `discovery_resources.py` - Resource discovery
- `stdio_server.py` - STDIO MCP server
- `install.sh` - Installation script

### HTTP Endpoints

When running `unified_server.py`:

- `GET /health` - Health check
- `POST /tools/call` - Execute tool
- `GET /tools/list` - List available tools
- `GET /resources/list` - List available resources
- `GET /resources/read` - Read resource
- `GET /stream/{task_id}` - SSE stream for workflow
- `POST /webhooks/register` - Register webhook

### Client Usage

```python
import requests

# Start workflow
response = requests.post('http://localhost:5060/tools/call', json={
    'name': 'dream_research',
    'arguments': {
        'task': 'Research quantum computing',
        'belter_count': 3,
        'stream': True
    }
})
task_id = response.json()['task_id']

# Subscribe to stream
import sseclient
events = sseclient.SSEClient(f'http://localhost:5060/stream/{task_id}')
for event in events:
    print(event.data)

# Check status
status = requests.get(f'http://localhost:5060/tools/call', json={
    'name': 'dreamwalker_status',
    'arguments': {'task_id': task_id}
})
```

### Best Practices

- Always use streaming for long workflows
- Set reasonable timeouts for workflows
- Clean up completed workflows periodically
- Monitor active workflow count
- Use webhooks for async notifications
- Implement proper error handling
- Log all workflow events
- Validate tool arguments before execution

### Dependencies

- `flask` - Web server
- `sse` - Server-Sent Events
- `orchestration/` - Orchestrator framework
- `llm_providers/` - LLM providers
- `data_fetching/` - Data clients
- `tools/` - Tool modules

### Port Configuration

Default: 5060

Configured in:
- `/etc/caddy/Caddyfile` (proxy rules)
- `/home/coolhand/service_manager.py` (service config)
- Environment variable `MCP_PORT`
