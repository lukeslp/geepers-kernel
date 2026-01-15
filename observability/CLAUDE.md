# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module: observability

Metrics collection, cost tracking, and monitoring capabilities for LLM provider calls and tool usage.

### Overview

The observability module provides:
- **CostTracker** - Real-time cost calculation for LLM API calls
- **MetricsCollector** - Tool usage tracking and analytics
- Budget monitoring and alerts
- Cost breakdown by provider, model, and time period

### CostTracker

Track and calculate LLM API costs:

```python
from observability import get_cost_tracker, CostTracker

# Get singleton instance
tracker = get_cost_tracker()

# Calculate cost for an API call
cost = tracker.calculate_cost(
    provider='openai',
    model='gpt-4o',
    prompt_tokens=1000,
    completion_tokens=500
)
print(f"Cost: ${cost:.4f}")

# Track cost
tracker.track_cost(
    provider='openai',
    model='gpt-4o',
    prompt_tokens=1000,
    completion_tokens=500,
    metadata={'task_id': 'task-123'}
)

# Get total cost
total = tracker.get_total_cost()
print(f"Total spent: ${total:.2f}")

# Get cost for today
today_cost = tracker.get_cost_for_date(date.today())

# Get breakdown by provider
breakdown = tracker.get_cost_breakdown()
for provider, cost in breakdown.by_provider.items():
    print(f"{provider}: ${cost:.4f}")
```

### Pricing Data

Current pricing per 1M tokens (as of November 2025):

```python
from observability.cost_tracker import PRICING

# Access pricing
openai_gpt4_pricing = PRICING['openai']['gpt-4o']
print(f"Prompt: ${openai_gpt4_pricing['prompt']}/1M tokens")
print(f"Completion: ${openai_gpt4_pricing['completion']}/1M tokens")

# Supported providers and models:
# - OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
# - Anthropic: claude-3-5-sonnet, claude-sonnet-4, claude-3-haiku, claude-3-opus
# - xAI: grok-beta, grok-2, grok-3
# - Mistral: mistral-small, mistral-medium, mistral-large
# - Cohere: command-light, command, command-r-plus
# - Gemini: gemini-1.5-flash, gemini-1.5-pro
# - Perplexity: sonar models
# - Groq: llama models
```

### Budget Monitoring

Set and monitor budgets:

```python
tracker = get_cost_tracker()

# Set daily budget
tracker.set_budget(
    amount=10.00,
    period='daily'
)

# Check if over budget
if tracker.is_over_budget():
    print("Warning: Over budget!")

# Get budget status
status = tracker.get_budget_status()
print(f"Spent: ${status['spent']:.2f} / ${status['budget']:.2f}")
print(f"Remaining: ${status['remaining']:.2f}")
```

### Cost Breakdown

Analyze costs by various dimensions:

```python
tracker = get_cost_tracker()

# Get breakdown
breakdown = tracker.get_cost_breakdown(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31)
)

print(f"Total: ${breakdown.total_cost:.2f}")

# By provider
for provider, cost in breakdown.by_provider.items():
    print(f"{provider}: ${cost:.4f}")

# By model
for model, cost in breakdown.by_model.items():
    print(f"{model}: ${cost:.4f}")

# By date
for date_str, cost in breakdown.by_date.items():
    print(f"{date_str}: ${cost:.4f}")
```

### MetricsCollector

Track tool usage and performance:

```python
from observability import get_metrics_collector, MetricsCollector

# Get singleton instance
metrics = get_metrics_collector()

# Track tool call
metrics.start_tool_call('arxiv_search')
# ... execute tool ...
metrics.end_tool_call('arxiv_search', success=True)

# Or use context manager
with metrics.track_tool_call('arxiv_search'):
    results = search_arxiv(query)

# Get metrics
tool_metrics = metrics.get_tool_metrics('arxiv_search')
print(f"Calls: {tool_metrics['count']}")
print(f"Success rate: {tool_metrics['success_rate']:.2%}")
print(f"Avg duration: {tool_metrics['avg_duration']:.2f}s")

# Get all metrics
all_metrics = metrics.get_all_metrics()
```

### Integration with Orchestrators

Track costs during orchestration:

```python
from orchestration import DreamCascadeOrchestrator
from observability import get_cost_tracker

tracker = get_cost_tracker()

# Before orchestration
start_cost = tracker.get_total_cost()

# Run orchestration
orchestrator = DreamCascadeOrchestrator(config, provider)
result = await orchestrator.execute_workflow(task)

# Calculate orchestration cost
orchestration_cost = tracker.get_total_cost() - start_cost
print(f"Orchestration cost: ${orchestration_cost:.4f}")

# Or use result.total_cost if available
print(f"From result: ${result.total_cost:.4f}")
```

### Auto-tracking with Provider Wrapper

Automatically track all provider calls:

```python
from observability import get_cost_tracker
from llm_providers import ProviderFactory

tracker = get_cost_tracker()

# Wrap provider
provider = ProviderFactory.get_provider('openai')

# Make calls - costs are automatically tracked
response = provider.complete(messages=[...])
# Cost is automatically calculated and tracked

# Check total
print(f"Total: ${tracker.get_total_cost():.2f}")
```

### Cost Data Models

```python
from observability import Cost, CostBreakdown
from datetime import datetime
from decimal import Decimal

# Individual cost entry
cost = Cost(
    timestamp=datetime.now(),
    provider='openai',
    model='gpt-4o',
    prompt_tokens=1000,
    completion_tokens=500,
    cost_usd=Decimal('0.0175'),
    metadata={'task_id': 'task-123'}
)

# Cost breakdown
breakdown = CostBreakdown(
    total_cost=Decimal('10.50'),
    by_provider={'openai': Decimal('5.00'), 'anthropic': Decimal('5.50')},
    by_model={'gpt-4o': Decimal('3.00'), 'claude-3-5-sonnet': Decimal('7.50')},
    by_date={'2024-01-01': Decimal('10.50')}
)
```

### Exporting Data

Export cost data for analysis:

```python
tracker = get_cost_tracker()

# Export to CSV
tracker.export_to_csv('/path/to/costs.csv')

# Export to JSON
tracker.export_to_json('/path/to/costs.json')

# Get raw data
all_costs = tracker.get_all_costs()
for cost in all_costs:
    print(f"{cost.timestamp}: ${cost.cost_usd} ({cost.provider}/{cost.model})")
```

### Alerts and Notifications

Set up cost alerts:

```python
tracker = get_cost_tracker()

# Set alert threshold
tracker.set_alert_threshold(
    amount=5.00,
    callback=lambda cost: print(f"Alert: ${cost:.2f} spent!")
)

# Alerts trigger when threshold is crossed
```

### Tool Call Metrics

Detailed tool performance tracking:

```python
from observability import ToolCallContext

metrics = get_metrics_collector()

# Manual tracking
context = metrics.start_tool_call('my_tool')
try:
    result = execute_tool()
    context.end(success=True, metadata={'result_count': len(result)})
except Exception as e:
    context.end(success=False, error=str(e))

# Context manager (recommended)
with metrics.track_tool_call('my_tool') as ctx:
    result = execute_tool()
    ctx.add_metadata({'result_count': len(result)})
```

### Testing

```python
import pytest
from observability import CostTracker
from decimal import Decimal

def test_cost_calculation():
    tracker = CostTracker()

    cost = tracker.calculate_cost(
        provider='openai',
        model='gpt-4o',
        prompt_tokens=1000,
        completion_tokens=500
    )

    # gpt-4o: $2.50/1M prompt, $10/1M completion
    # (1000 * 2.50 + 500 * 10.00) / 1,000,000 = 0.0075
    assert cost == Decimal('0.0075')

@pytest.mark.asyncio
async def test_metrics_collection():
    metrics = MetricsCollector()

    with metrics.track_tool_call('test_tool'):
        await asyncio.sleep(0.1)

    tool_metrics = metrics.get_tool_metrics('test_tool')
    assert tool_metrics['count'] == 1
    assert tool_metrics['success_rate'] == 1.0
```

### Files in This Module

- `cost_tracker.py` - Cost tracking and calculation
- `metrics.py` - Tool usage metrics collection
- `__init__.py` - Module exports

### Persistence

Save and load tracking data:

```python
tracker = get_cost_tracker()

# Save state
tracker.save_state('/path/to/state.json')

# Load state
tracker.load_state('/path/to/state.json')

# Auto-save on exit
import atexit
atexit.register(lambda: tracker.save_state('/path/to/state.json'))
```

### Real-time Monitoring

Monitor costs in real-time:

```python
tracker = get_cost_tracker()

# Get current rate
rate = tracker.get_current_rate()  # $/hour
print(f"Current rate: ${rate:.2f}/hour")

# Estimate cost for task
estimated = tracker.estimate_cost(
    provider='openai',
    model='gpt-4o',
    estimated_tokens=10000
)
print(f"Estimated: ${estimated:.4f}")
```

### Best Practices

- Always use singleton instances (`get_cost_tracker()`, `get_metrics_collector()`)
- Track costs for all LLM API calls
- Set reasonable budgets for development vs production
- Export cost data regularly for analysis
- Monitor metrics to identify bottlenecks
- Use context managers for automatic tracking
- Save state periodically to avoid data loss
- Review cost breakdowns regularly
- Set alerts for budget thresholds
- Use metadata to track costs by task/project

### Common Patterns

#### Per-Request Cost Tracking
```python
tracker = get_cost_tracker()

async def handle_request(request):
    start_cost = tracker.get_total_cost()

    # Process request
    result = await process(request)

    request_cost = tracker.get_total_cost() - start_cost
    return {
        'result': result,
        'cost': float(request_cost)
    }
```

#### Budget-Aware Execution
```python
tracker = get_cost_tracker()
tracker.set_budget(amount=10.00, period='daily')

if tracker.is_over_budget():
    raise Exception("Daily budget exceeded")

# Proceed with API call
result = provider.complete(messages)
```

#### Cost Comparison
```python
tracker = get_cost_tracker()

# Compare costs for different models
models = ['gpt-4o', 'gpt-4o-mini', 'claude-3-haiku']
for model in models:
    cost = tracker.calculate_cost(
        provider='openai' if 'gpt' in model else 'anthropic',
        model=model,
        prompt_tokens=1000,
        completion_tokens=1000
    )
    print(f"{model}: ${cost:.4f}")
```

### Dependencies

- Standard library: `datetime`, `decimal`, `collections`
- Optional: `pandas` for advanced analytics

### Integration Points

- Automatically integrated with `llm_providers/` when using ProviderFactory
- Used by `orchestration/` for workflow cost tracking
- Exposed via `mcp/` server for monitoring
- Works with `tools/` registry for tool metrics
