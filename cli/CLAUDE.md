# CLAUDE.md
<!-- Navigation: ~/shared/cli/CLAUDE.md -->
<!-- Parent: ~/shared/CLAUDE.md -->
<!-- Map: ~/CLAUDE_MAP.md -->

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module: cli

Command-line interface utilities for testing and managing the shared library components.

### Overview

The cli module provides command-line tools for:
- **ping_providers.py** - Test LLM provider connectivity and API keys
- **todoist/** - Todoist task management CLI

---

### todoist/todoist_cli.py

Command-line interface for Todoist task management using the official SDK.

```bash
# Via symlink (after sourcing bashrc)
todoist tasks                         # List all active tasks
todoist tasks -p "Work"               # Filter tasks by project
todoist projects                      # List all projects
todoist add "Buy groceries"           # Add a simple task
todoist add "Meeting" -d "tomorrow"   # Add task with due date
todoist add "Urgent" -P 4             # Add high-priority task (P1)
todoist complete <task_id>            # Mark task as complete
todoist delete <task_id>              # Delete a task
todoist get <task_id>                 # View task details
todoist update <task_id> --content "New text"

# Direct invocation
python /home/coolhand/shared/cli/todoist/todoist_cli.py tasks
```

#### Environment Setup

```bash
export TODOIST_API_KEY="your-api-key"
# Already configured in ~/.bashrc
```

#### Priority Mapping

| API Value | UI Display | CLI Flag |
|-----------|------------|----------|
| 4 | P1 (High) | `-P 4` |
| 3 | P2 | `-P 3` |
| 2 | P3 | `-P 2` |
| 1 | P4 (Normal) | `-P 1` (default) |

#### Command Aliases

| Primary | Aliases |
|---------|---------|
| `tasks` | `ls`, `list` |
| `projects` | `proj` |
| `add` | `new`, `create` |
| `complete` | `done`, `close`, `finish` |
| `delete` | `rm`, `remove` |
| `get` | `show`, `view` |
| `update` | `edit`, `modify` |

---

### ping_providers.py

Unified tool for testing all LLM provider APIs:

```bash
# Test single provider
python /home/coolhand/shared/cli/ping_providers.py --provider openai

# Test all providers
python /home/coolhand/shared/cli/ping_providers.py --all

# List available providers
python /home/coolhand/shared/cli/ping_providers.py --list

# Test specific provider with custom model
python /home/coolhand/shared/cli/ping_providers.py --provider xai --model grok-3

# Verbose output
python /home/coolhand/shared/cli/ping_providers.py --provider anthropic --verbose
```

### Supported Providers

The tool can test:
- **openai** - OpenAI (GPT-4, GPT-3.5)
- **anthropic** - Anthropic (Claude)
- **xai** - xAI (Grok)
- **mistral** - Mistral AI
- **cohere** - Cohere
- **gemini** - Google Gemini
- **perplexity** - Perplexity
- **groq** - Groq
- **huggingface** - HuggingFace

### Usage Examples

#### Test OpenAI
```bash
$ python ping_providers.py --provider openai

Testing OpenAI...
✓ API key found
✓ Connection successful
✓ Model: gpt-4o
✓ Response: Hello! How can I assist you today?
✓ Tokens used: 15

OpenAI: OK
```

#### Test All Providers
```bash
$ python ping_providers.py --all

Testing all providers...

OpenAI: ✓ OK
Anthropic: ✓ OK
xAI: ✓ OK
Mistral: ✓ OK
Cohere: ✓ OK
Gemini: ✓ OK
Perplexity: ✗ FAILED (API key not found)
Groq: ✓ OK
HuggingFace: ✗ FAILED (Connection timeout)

Results: 7/9 providers OK
```

#### List Providers
```bash
$ python ping_providers.py --list

Available providers:
- openai (OpenAI)
- anthropic (Anthropic/Claude)
- xai (xAI/Grok)
- mistral (Mistral AI)
- cohere (Cohere)
- gemini (Google Gemini)
- perplexity (Perplexity)
- groq (Groq)
- huggingface (HuggingFace)
```

### Command-Line Options

```
usage: ping_providers.py [-h] [--provider PROVIDER] [--all] [--list]
                        [--model MODEL] [--verbose]

Test LLM provider connectivity

optional arguments:
  -h, --help           show this help message and exit
  --provider PROVIDER  Provider to test (e.g., openai, anthropic, xai)
  --all                Test all providers
  --list               List available providers
  --model MODEL        Specific model to test (default: provider default)
  --verbose, -v        Verbose output
```

### Environment Variables

The tool looks for API keys in environment variables:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export XAI_API_KEY=xai-...
export MISTRAL_API_KEY=...
export COHERE_API_KEY=...
export GOOGLE_API_KEY=...
export PERPLEXITY_API_KEY=...
export GROQ_API_KEY=...
export HUGGINGFACE_API_KEY=...
```

Or loads from `/home/coolhand/API_KEYS.md` via ConfigManager.

### Provider Configuration

```python
PROVIDERS = {
    'openai': {
        'name': 'OpenAI',
        'env_key': 'OPENAI_API_KEY',
        'base_url': None,
        'package': 'openai',
        'default_model': 'gpt-4o'
    },
    'anthropic': {
        'name': 'Anthropic (Claude)',
        'env_key': 'ANTHROPIC_API_KEY',
        'base_url': None,
        'package': 'anthropic',
        'default_model': 'claude-3-5-sonnet'
    },
    'xai': {
        'name': 'xAI (Grok)',
        'env_key': 'XAI_API_KEY',
        'base_url': 'https://api.x.ai/v1',
        'package': 'openai',
        'default_model': 'grok-3'
    }
}
```

### Exit Codes

- **0** - Success
- **1** - One or more providers failed
- **2** - Command-line error

### Programmatic Usage

```python
#!/usr/bin/env python3
from cli.ping_providers import ping_provider, ping_all_providers

# Test single provider
result = ping_provider('openai')
if result['success']:
    print(f"OpenAI OK: {result['message']}")
else:
    print(f"OpenAI Failed: {result['error']}")

# Test all
results = ping_all_providers()
for provider, result in results.items():
    status = '✓' if result['success'] else '✗'
    print(f"{provider}: {status}")
```

### Integration with ConfigManager

```python
from config import ConfigManager
from cli.ping_providers import ping_provider

config = ConfigManager()

# Test provider with config
for provider in ['openai', 'anthropic', 'xai']:
    api_key = config.get_api_key(provider)
    if api_key:
        result = ping_provider(provider)
        print(f"{provider}: {'OK' if result['success'] else 'FAILED'}")
```

### Testing

```python
import pytest
from cli.ping_providers import ping_provider

def test_ping_openai():
    """Test OpenAI provider ping"""
    result = ping_provider('openai')
    assert 'success' in result
    assert 'message' in result or 'error' in result

@pytest.mark.skipif(
    not os.getenv('ANTHROPIC_API_KEY'),
    reason="ANTHROPIC_API_KEY not set"
)
def test_ping_anthropic():
    """Test Anthropic provider ping"""
    result = ping_provider('anthropic')
    assert result['success'] is True
```

### Files in This Module

- `ping_providers.py` - LLM provider connectivity tester

### Future CLI Tools

Planned additions:
- `test_orchestrators.py` - Test orchestrator patterns
- `benchmark_providers.py` - Benchmark provider performance
- `cost_calculator.py` - Calculate costs for workflows
- `migrate_data.py` - Data migration utilities
- `export_metrics.py` - Export metrics and costs

### Best Practices

- Run `ping_providers.py --all` after setting up new API keys
- Use before deployment to verify all providers are accessible
- Include in CI/CD pipeline for integration testing
- Check regularly to detect API changes or outages
- Use verbose mode for debugging connectivity issues

### Common Patterns

#### Verify Before Deployment
```bash
#!/bin/bash
# pre-deploy.sh

echo "Testing provider connectivity..."
python /home/coolhand/shared/cli/ping_providers.py --all

if [ $? -ne 0 ]; then
    echo "Provider tests failed, aborting deployment"
    exit 1
fi

echo "All providers OK, proceeding with deployment"
```

#### Health Check Script
```bash
#!/bin/bash
# health-check.sh

# Run hourly via cron
python /home/coolhand/shared/cli/ping_providers.py --all --verbose > /var/log/provider-health.log 2>&1
```

#### Selective Testing
```bash
# Test only critical providers
for provider in openai anthropic xai; do
    python ping_providers.py --provider $provider || echo "$provider failed"
done
```

### Dependencies

- Standard library
- `llm_providers/` - Provider implementations
- `config/` - Configuration management

### Installation

```bash
# Make executable
chmod +x /home/coolhand/shared/cli/ping_providers.py

# Add to PATH (optional)
export PATH=$PATH:/home/coolhand/shared/cli

# Or create symlink
ln -s /home/coolhand/shared/cli/ping_providers.py /usr/local/bin/ping-providers
```

### Troubleshooting

**API Key Not Found:**
```bash
# Check environment
echo $OPENAI_API_KEY

# Or check config
python -c "from config import ConfigManager; print(ConfigManager().get_api_key('openai'))"
```

**Connection Timeout:**
```bash
# Test with verbose output
python ping_providers.py --provider openai --verbose

# Check network
curl -I https://api.openai.com

# Check firewall
sudo ufw status
```

**Import Errors:**
```bash
# Ensure shared library is in Python path
export PYTHONPATH=/home/coolhand/shared:$PYTHONPATH

# Or install as package
cd /home/coolhand/shared
pip install -e .
```

### Integration Examples

#### With Service Manager
```python
# In service startup script
from cli.ping_providers import ping_provider

# Verify provider before starting service
result = ping_provider('xai')
if not result['success']:
    logger.error(f"xAI provider unavailable: {result['error']}")
    sys.exit(1)

# Start service
start_service()
```

#### With Monitoring
```python
# In monitoring script
from cli.ping_providers import ping_all_providers
from observability import get_metrics_collector

metrics = get_metrics_collector()
results = ping_all_providers()

for provider, result in results.items():
    metrics.record_health_check(
        provider=provider,
        success=result['success']
    )
```

### Output Formats

**Standard Output:**
```
Testing OpenAI...
✓ API key found
✓ Connection successful
✓ Response received
OpenAI: OK
```

**Verbose Output:**
```
Testing OpenAI...
Provider: OpenAI
API Key: sk-...xyz (found)
Base URL: https://api.openai.com/v1
Model: gpt-4o
Request: Sending test completion...
Response: Hello! How can I assist you today?
Tokens: 15 (input: 5, output: 10)
Latency: 1.23s
OpenAI: OK
```

**JSON Output (programmatic):**
```json
{
  "success": true,
  "provider": "openai",
  "model": "gpt-4o",
  "response": "Hello! How can I assist you today?",
  "tokens": {"input": 5, "output": 10, "total": 15},
  "latency": 1.23,
  "timestamp": "2024-01-01T12:00:00Z"
}
```
