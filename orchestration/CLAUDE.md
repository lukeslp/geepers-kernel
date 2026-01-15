# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module: orchestration

Comprehensive framework for building multi-agent orchestrator workflows with standardized patterns, streaming support, and document generation.

### Overview

The orchestration framework provides:
- Abstract base class for custom orchestrators
- 5 built-in orchestration patterns
- Streaming progress callbacks
- Cost tracking and metrics
- Document generation integration
- Standardized data models

### Core Concepts

All orchestrators follow a 3-step workflow:

1. **Decompose Task** → `List[SubTask]`
2. **Execute Subtasks** → `List[AgentResult]`
3. **Synthesize Results** → `OrchestratorResult`

### Built-in Orchestrators

#### DreamCascadeOrchestrator (formerly Beltalowda)

Hierarchical research with 3 agent tiers:

```python
from orchestration import DreamCascadeOrchestrator, DreamCascadeConfig
from llm_providers import ProviderFactory

config = DreamCascadeConfig(
    belter_count=3,      # Tier 1: Quick searches
    drummer_count=2,     # Tier 2: Analysis
    camina_count=1,      # Tier 3: Synthesis
    primary_model='grok-3'
)

orchestrator = DreamCascadeOrchestrator(
    config=config,
    provider=ProviderFactory.get_provider('xai')
)

result = await orchestrator.execute_workflow(
    task="Research quantum computing applications in cryptography"
)
```

**Use for**: Deep research, hierarchical analysis, multi-stage workflows

#### DreamSwarmOrchestrator (formerly Swarm)

Parallel multi-domain search:

```python
from orchestration import DreamSwarmOrchestrator, DreamSwarmConfig

config = DreamSwarmConfig(
    num_agents=5,
    domains=['arxiv', 'github', 'news', 'wikipedia'],
    max_parallel=3
)

orchestrator = DreamSwarmOrchestrator(config, provider)
result = await orchestrator.execute_workflow(
    task="Find latest AI safety research"
)
```

**Use for**: Broad information gathering, parallel searches, domain-specific queries

#### SequentialOrchestrator

Step-by-step execution with custom handlers:

```python
from orchestration import SequentialOrchestrator, OrchestratorConfig

config = OrchestratorConfig(
    num_agents=3,
    steps=['research', 'analyze', 'synthesize']
)

def custom_handler(step, context):
    # Custom logic per step
    return result

orchestrator = SequentialOrchestrator(
    config,
    provider,
    step_handlers={'research': custom_handler}
)
```

**Use for**: Pipelines, staged workflows, sequential dependencies

#### ConditionalOrchestrator

Runtime branching based on conditions:

```python
from orchestration import ConditionalOrchestrator

def condition_fn(context):
    return context.get('complexity') > 0.7

orchestrator = ConditionalOrchestrator(
    config,
    provider,
    condition=condition_fn,
    true_branch=complex_handler,
    false_branch=simple_handler
)
```

**Use for**: Adaptive workflows, conditional logic, decision trees

#### IterativeOrchestrator

Looped refinement until convergence:

```python
from orchestration import IterativeOrchestrator

orchestrator = IterativeOrchestrator(
    config,
    provider,
    max_iterations=5,
    convergence_fn=lambda results: results['score'] > 0.9
)
```

**Use for**: Optimization, iterative improvement, refinement loops

### Building Custom Orchestrators

Extend `BaseOrchestrator` and implement 3 required methods:

```python
from orchestration import BaseOrchestrator, OrchestratorConfig, SubTask, AgentResult

class MyOrchestrator(BaseOrchestrator):
    async def decompose_task(self, task: str, context: dict = None) -> List[SubTask]:
        """Break task into subtasks"""
        return [
            SubTask(
                id='subtask-1',
                description='Research topic',
                agent_type='researcher',
                priority=1
            ),
            SubTask(
                id='subtask-2',
                description='Analyze findings',
                agent_type='analyst',
                priority=2
            )
        ]

    async def execute_subtask(self, subtask: SubTask, context: dict = None) -> AgentResult:
        """Execute a single subtask"""
        # Use self.provider to call LLM
        response = self.provider.complete(
            messages=[{'role': 'user', 'content': subtask.description}]
        )

        return AgentResult(
            subtask_id=subtask.id,
            content=response.content,
            status='completed',
            metadata={'tokens': response.usage}
        )

    async def synthesize_results(
        self,
        agent_results: List[AgentResult],
        context: dict = None
    ) -> dict:
        """Combine results into final output"""
        combined = '\n\n'.join([r.content for r in agent_results])

        # Optional: Use LLM to synthesize
        synthesis = self.provider.complete(
            messages=[{
                'role': 'user',
                'content': f'Synthesize these results:\n\n{combined}'
            }]
        )

        return {
            'summary': synthesis.content,
            'raw_results': agent_results
        }

# Use it
config = OrchestratorConfig(num_agents=2)
orchestrator = MyOrchestrator(config, provider)
result = await orchestrator.execute_workflow("My task")
```

### Configuration

```python
from orchestration import OrchestratorConfig

config = OrchestratorConfig(
    num_agents=5,
    primary_model='grok-3',
    fallback_model='gpt-4',
    max_retries=3,
    timeout_seconds=300,
    enable_streaming=True,
    enable_cost_tracking=True,
    enable_document_generation=False,
    parallel_execution=True,
    max_parallel=3
)

# Validate before use
errors = config.validate()
if errors:
    print(f"Config errors: {errors}")
```

### Streaming Progress

```python
async def progress_callback(event):
    print(f"[{event.event_type}] {event.message}")
    if event.progress:
        print(f"Progress: {event.progress}%")

orchestrator.stream_callback = progress_callback
result = await orchestrator.execute_workflow(task)
```

Event types: `TASK_STARTED`, `SUBTASK_CREATED`, `SUBTASK_COMPLETED`, `SYNTHESIS_STARTED`, `SYNTHESIS_COMPLETED`, `TASK_COMPLETED`, `ERROR`

### Data Models

```python
from orchestration import SubTask, AgentResult, OrchestratorResult, TaskStatus, AgentType

# SubTask
subtask = SubTask(
    id='task-1',
    description='Analyze data',
    agent_type=AgentType.ANALYST,
    priority=1,
    dependencies=['task-0']
)

# AgentResult
result = AgentResult(
    subtask_id='task-1',
    content='Analysis results...',
    status=TaskStatus.COMPLETED,
    tokens_used=1500,
    cost=0.003,
    metadata={'model': 'grok-3'}
)

# OrchestratorResult
orchestrator_result = OrchestratorResult(
    task_id='workflow-1',
    status=TaskStatus.COMPLETED,
    result={'summary': '...', 'details': [...]},
    agent_results=[...],
    total_cost=0.05,
    execution_time=45.2,
    metadata={}
)
```

### Utilities

```python
from orchestration import (
    ProgressTracker,
    CostTracker,
    calculate_progress,
    format_duration,
    format_cost,
    retry_async
)

# Progress tracking
tracker = ProgressTracker(total_tasks=10)
tracker.update(completed=3)
print(f"{tracker.percentage()}% complete")

# Cost tracking
cost_tracker = CostTracker()
cost_tracker.add_cost(0.05, metadata={'model': 'grok-3'})
print(f"Total: ${cost_tracker.total_cost:.4f}")

# Retry with exponential backoff
@retry_async(max_retries=3, base_delay=1.0)
async def unstable_api_call():
    return await api.fetch()
```

### Document Generation

Orchestrators can auto-generate reports:

```python
config = OrchestratorConfig(
    enable_document_generation=True,
    output_formats=['pdf', 'markdown']
)

result = await orchestrator.execute_workflow(task)
# result.documents contains generated files
```

### Importing from Other Projects

```python
# From other projects on this server
import sys
sys.path.insert(0, '/home/coolhand/shared')

from orchestration import DreamCascadeOrchestrator, DreamCascadeConfig
from llm_providers import ProviderFactory

provider = ProviderFactory.get_provider('xai')
orchestrator = DreamCascadeOrchestrator(
    config=DreamCascadeConfig(),
    provider=provider
)
```

### Testing

```python
import pytest
from orchestration import BaseOrchestrator, OrchestratorConfig

@pytest.mark.asyncio
async def test_custom_orchestrator():
    orchestrator = MyOrchestrator(
        config=OrchestratorConfig(num_agents=2),
        provider=mock_provider
    )

    result = await orchestrator.execute_workflow("Test task")
    assert result.status == 'completed'
    assert len(result.agent_results) > 0
```

### Files in This Module

- `base_orchestrator.py` - Abstract base class
- `dream_cascade_orchestrator.py` - Hierarchical research (Belter/Drummer/Camina)
- `dream_swarm_orchestrator.py` - Multi-domain parallel search
- `sequential_orchestrator.py` - Step-by-step execution
- `conditional_orchestrator.py` - Branching logic
- `iterative_orchestrator.py` - Refinement loops
- `models.py` - Data models (SubTask, AgentResult, etc.)
- `config.py` - Configuration classes
- `utils.py` - Progress tracking, cost tracking, helpers
- `streaming.py` - Streaming callbacks and helpers
- `ORCHESTRATOR_GUIDE.md` - Detailed implementation guide
- `ORCHESTRATOR_SELECTION_GUIDE.md` - Pattern selection guide
- `ORCHESTRATOR_BENCHMARKS.md` - Performance benchmarks
- `templates/` - Code templates for custom orchestrators

### Naming Notes

- "Dream Cascade" = new name for "Beltalowda" pattern
- "Dream Swarm" = new name for "Swarm" pattern
- Legacy class names (`BeltalowdaOrchestrator`, `SwarmOrchestrator`) still work as aliases
- Config classes also aliased: `BeltalowdaConfig` → `DreamCascadeConfig`

### Dependencies

- `asyncio` for async execution
- LLM provider from `llm_providers/`
- Optional: `document_generation/` for report generation

### Common Patterns

#### Multi-provider orchestration
```python
# Use different providers for different stages
config = DreamCascadeConfig(
    belter_model='groq-llama',     # Fast, cheap for tier 1
    drummer_model='grok-3',        # Balanced for tier 2
    camina_model='claude-3.5'      # Best for final synthesis
)
```

#### Error handling
```python
try:
    result = await orchestrator.execute_workflow(task)
except Exception as e:
    logger.error(f"Orchestration failed: {e}")
    # Partial results may be available
    if hasattr(e, 'partial_results'):
        return e.partial_results
```

#### Cost optimization
```python
config = OrchestratorConfig(
    enable_cost_tracking=True,
    max_cost=1.00  # Stop if cost exceeds $1
)
```

### Best Practices

- Always validate config before creating orchestrator
- Use streaming for long-running workflows
- Enable cost tracking for production use
- Implement proper error handling in custom orchestrators
- Use type hints for subtask and result models
- Log progress events for debugging
- Test with mock providers before using real APIs
