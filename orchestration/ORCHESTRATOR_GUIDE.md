# Building Custom Orchestrators

Comprehensive guide to building custom orchestrator patterns using the BaseOrchestrator framework.

**Author:** Luke Steuber
**Version:** 1.0.0

## Table of Contents

- [Overview](#overview)
- [BaseOrchestrator Framework](#baseorchestrator-framework)
- [Quick Start](#quick-start)
- [Detailed Implementation Guide](#detailed-implementation-guide)
- [Best Practices](#best-practices)
- [Advanced Patterns](#advanced-patterns)
- [Testing and Debugging](#testing-and-debugging)
- [Deployment](#deployment)

## Overview

The BaseOrchestrator framework provides a standardized pattern for building AI orchestrator agents that coordinate multiple LLM calls to solve complex tasks. By inheriting from `BaseOrchestrator` and implementing 3 abstract methods, you can create sophisticated multi-agent workflows with minimal boilerplate.

### What is an Orchestrator?

An orchestrator is a system that:
1. **Decomposes** complex tasks into manageable subtasks
2. **Executes** subtasks (often in parallel) using specialized agents
3. **Synthesizes** results into a coherent final output
4. **Generates** deliverable artifacts (documents, reports, etc.)

### Why Use BaseOrchestrator?

**Benefits:**
- **Standardization**: Consistent workflow pattern across all orchestrators
- **Streaming Built-in**: Real-time progress updates via SSE/webhooks
- **Document Generation**: Professional PDF/DOCX/Markdown output
- **Error Handling**: Automatic retries, timeouts, graceful degradation
- **Cost Tracking**: Built-in cost and token tracking
- **Parallelization**: Semaphore-based concurrency control
- **Extensibility**: Easy to customize while maintaining core patterns

**Use Cases:**
- Research synthesis (Beltalowda pattern)
- Multi-source search (Swarm pattern)
- Content generation pipelines
- Data analysis workflows
- Competitive intelligence gathering
- Literature reviews
- Market analysis

### Built-in Patterns

The shared library now ships with several orchestration patterns ready to use:

- **BeltalowdaOrchestrator** – hierarchical research with Belter/Drummer/Camina tiers.
- **SwarmOrchestrator** – multi-domain exploratory search.
- **SequentialOrchestrator** *(new)* – deterministic staged execution with optional per-step handlers.
- **ConditionalOrchestrator** *(new)* – runtime branch selection driven by context or evaluator callbacks.
- **IterativeOrchestrator** *(new)* – looped refinement until a success predicate is met.

Refer to `ORCHESTRATOR_SELECTION_GUIDE.md` for decision matrices and `ORCHESTRATOR_BENCHMARKS.md` for performance characteristics.

## BaseOrchestrator Framework

### Architecture

```
BaseOrchestrator
├── execute_workflow() [implemented]
│   └── Standard template pattern:
│       1. decompose_task() [abstract - you implement]
│       2. execute_subtask() [abstract - you implement]
│       3. synthesize_results() [abstract - you implement]
│       4. generate_documents() [implemented]
│       5. Return structured OrchestratorResult
│
├── Helper Methods [implemented]
│   ├── _execute_agents_parallel()
│   ├── _execute_agents_sequential()
│   ├── _emit_event()
│   └── _generate_documents()
│
└── Configuration
    └── OrchestratorConfig [extendable]
```

### The 3 Abstract Methods

You **must** implement these 3 methods:

```python
@abstractmethod
async def decompose_task(
    self,
    task: str,
    context: Optional[Dict[str, Any]] = None
) -> List[SubTask]:
    """Break task into subtasks.

    Args:
        task: High-level task description
        context: Optional additional context

    Returns:
        List of SubTask objects with:
        - id: Unique identifier
        - description: What this subtask does
        - context: Subtask-specific data
        - agent_type: Type of agent to use
        - specialization: Optional specialization
        - priority: Execution priority (0-10)
        - dependencies: List of subtask IDs this depends on
    """
    pass

@abstractmethod
async def execute_subtask(
    self,
    subtask: SubTask,
    context: Optional[Dict[str, Any]] = None
) -> AgentResult:
    """Execute a single subtask.

    Args:
        subtask: SubTask to execute
        context: Optional execution context

    Returns:
        AgentResult with:
        - agent_id: Unique agent identifier
        - agent_type: Agent type used
        - status: 'success' | 'failed' | 'timeout'
        - result: Agent's output (string)
        - tokens_used: Token count
        - cost: Execution cost ($)
        - execution_time: Seconds taken
        - metadata: Additional data
    """
    pass

@abstractmethod
async def synthesize_results(
    self,
    agent_results: List[AgentResult],
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Synthesize agent results into final output.

    Args:
        agent_results: List of completed AgentResults
        context: Optional synthesis context

    Returns:
        Final synthesized report (string, typically Markdown)
    """
    pass
```

### Workflow Execution Pattern

The base class provides `execute_workflow()` which orchestrates the full workflow:

```python
async def execute_workflow(
    self,
    task: str,
    title: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    stream_callback: Optional[Callable] = None
) -> OrchestratorResult:
    """Standard workflow template - DO NOT OVERRIDE."""

    # 1. Decompose task
    subtasks = await self.decompose_task(task, context)
    self._emit_event('task_decomposed', {'subtask_count': len(subtasks)})

    # 2. Execute subtasks (parallel or sequential based on config)
    if self.config.parallel_execution:
        agent_results = await self._execute_agents_parallel(subtasks, context)
    else:
        agent_results = await self._execute_agents_sequential(subtasks, context)

    # 3. Synthesize results
    final_synthesis = await self.synthesize_results(agent_results, context)
    self._emit_event('synthesis_completed', {'output_length': len(final_synthesis)})

    # 4. Generate documents (if enabled)
    documents = []
    if self.config.generate_documents:
        documents = await self._generate_documents(final_synthesis, title, context)

    # 5. Return structured result
    return OrchestratorResult(
        task_id=self.task_id,
        title=title or task[:50],
        status=TaskStatus.COMPLETED,
        agent_results=agent_results,
        synthesis_results=[],
        final_synthesis=final_synthesis,
        execution_time=total_time,
        total_cost=total_cost,
        generated_documents=documents
    )
```

## Quick Start

### Step 1: Copy the Template

```bash
cp /home/coolhand/shared/orchestration/templates/orchestrator_template.py \
   /home/coolhand/shared/orchestration/my_orchestrator.py
```

### Step 2: Implement the 3 Methods

```python
from orchestration import BaseOrchestrator, SubTask, AgentResult, AgentType
from orchestration.config import OrchestratorConfig
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class MyOrchestratorConfig(OrchestratorConfig):
    """Custom configuration for MyOrchestrator."""
    my_custom_setting: str = "default_value"

class MyOrchestrator(BaseOrchestrator):
    """Custom orchestrator for [describe your use case]."""

    def __init__(self, config: Optional[MyOrchestratorConfig] = None):
        super().__init__(config or MyOrchestratorConfig())

    async def decompose_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[SubTask]:
        """Break task into subtasks using LLM."""

        # Use LLM to decompose task
        from llm_providers.xai_provider import XAIProvider
        provider = XAIProvider()

        prompt = f"""Break down this task into 5-10 specific subtasks:

Task: {task}

Return JSON array of subtasks with format:
[
  {{"description": "Subtask 1 description", "priority": 0}},
  {{"description": "Subtask 2 description", "priority": 1}}
]
"""

        response = await provider.generate(
            model="grok-4-fast",
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response and create SubTask objects
        import json
        subtask_data = json.loads(response['content'])

        return [
            SubTask(
                id=f"task-{i}",
                description=st['description'],
                context={},
                agent_type=AgentType.RESEARCH,
                specialization=None,
                priority=st.get('priority', i),
                dependencies=[]
            )
            for i, st in enumerate(subtask_data)
        ]

    async def execute_subtask(
        self,
        subtask: SubTask,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """Execute subtask using LLM agent."""

        from llm_providers.xai_provider import XAIProvider
        import time

        provider = XAIProvider()
        start_time = time.time()

        # Execute subtask
        prompt = f"""Execute this research task:

{subtask.description}

Provide comprehensive findings with sources."""

        try:
            response = await provider.generate(
                model=self.config.agent_model,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.config.timeout_seconds
            )

            return AgentResult(
                agent_id=subtask.id,
                agent_type=subtask.agent_type,
                specialization=subtask.specialization,
                status='success',
                result=response['content'],
                tokens_used=response.get('tokens_used', 0),
                cost=response.get('cost', 0.0),
                execution_time=time.time() - start_time,
                metadata={'model': self.config.agent_model}
            )

        except Exception as e:
            return AgentResult(
                agent_id=subtask.id,
                agent_type=subtask.agent_type,
                status='failed',
                result="",
                error=str(e),
                tokens_used=0,
                cost=0.0,
                execution_time=time.time() - start_time,
                metadata={}
            )

    async def synthesize_results(
        self,
        agent_results: List[AgentResult],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Synthesize all agent results into final report."""

        from llm_providers.xai_provider import XAIProvider
        provider = XAIProvider()

        # Combine agent results
        combined_findings = "\n\n".join([
            f"## Finding {i+1}\n{result.result}"
            for i, result in enumerate(agent_results)
            if result.status == 'success'
        ])

        # Synthesize with LLM
        prompt = f"""Synthesize these research findings into a comprehensive report:

{combined_findings}

Create a well-structured report with:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Conclusions

Format in Markdown."""

        response = await provider.generate(
            model=self.config.primary_model,
            messages=[{"role": "user", "content": prompt}]
        )

        return response['content']
```

### Step 3: Register with MCP Server

Add your orchestrator to `/home/coolhand/shared/mcp/unified_server.py`:

```python
from orchestration.my_orchestrator import MyOrchestrator, MyOrchestratorConfig

class UnifiedMCPServer:
    # ... existing code ...

    async def tool_my_custom_workflow(
        self,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute my custom workflow."""

        try:
            # Create task ID
            task_id = f"myorch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            # Create config from arguments
            config = MyOrchestratorConfig(
                num_agents=arguments.get('num_agents', 5),
                my_custom_setting=arguments.get('my_custom_setting', 'default')
            )

            # Create orchestrator
            orchestrator = MyOrchestrator(config)

            # Create streaming callback
            async def stream_callback(event_type: str, data: Dict[str, Any]):
                await self.streaming_bridge.emit_event(task_id, event_type, data)

            # Execute workflow asynchronously
            async def run_workflow():
                result = await orchestrator.execute_workflow(
                    task=arguments['task'],
                    title=arguments.get('title'),
                    context=arguments.get('context', {}),
                    stream_callback=stream_callback
                )
                # Store result
                self._results[task_id] = result

            # Start workflow in background
            asyncio.create_task(run_workflow())

            return {
                'success': True,
                'task_id': task_id,
                'status': 'running',
                'stream_url': f'/stream/{task_id}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
```

## Detailed Implementation Guide

### Decomposition Strategies

#### 1. LLM-Based Decomposition (Recommended)

Let the LLM break down the task intelligently:

```python
async def decompose_task(self, task: str, context: Optional[Dict] = None) -> List[SubTask]:
    """LLM-based task decomposition."""

    prompt = f"""You are a task planning expert. Break down this complex task into {self.config.num_agents} specific, actionable subtasks.

Task: {task}

Requirements:
- Each subtask should be independently executable
- Subtasks should collectively cover the entire task
- Assign appropriate priority (0-10, higher = more important)
- Identify dependencies between subtasks

Return JSON array:
[
  {{
    "description": "Specific subtask description",
    "priority": 5,
    "dependencies": ["task-0"],  // IDs of tasks this depends on
    "specialization": "optional specialization"
  }}
]
"""

    response = await self.provider.generate(
        model="grok-3",
        messages=[{"role": "user", "content": prompt}]
    )

    subtasks_data = json.loads(response['content'])

    return [
        SubTask(
            id=f"task-{i}",
            description=st['description'],
            context=context or {},
            agent_type=AgentType.RESEARCH,
            specialization=st.get('specialization'),
            priority=st.get('priority', i),
            dependencies=st.get('dependencies', [])
        )
        for i, st in enumerate(subtasks_data)
    ]
```

#### 2. Keyword-Based Decomposition

Extract keywords and create targeted subtasks:

```python
async def decompose_task(self, task: str, context: Optional[Dict] = None) -> List[SubTask]:
    """Keyword-based decomposition for Swarm-style searches."""

    # Extract keywords from query
    keywords = self._extract_keywords(task)

    # Detect agent types needed
    agent_types = self._detect_agent_types(task)

    subtasks = []
    for i, (keyword, agent_type) in enumerate(zip(keywords, agent_types)):
        subtasks.append(SubTask(
            id=f"search-{i}",
            description=f"Search for {keyword} using {agent_type} specialist",
            context={'keyword': keyword},
            agent_type=agent_type,
            specialization=keyword,
            priority=0,
            dependencies=[]
        ))

    return subtasks

def _detect_agent_types(self, query: str) -> List[AgentType]:
    """Detect agent types from query keywords."""

    query_lower = query.lower()
    agent_types = []

    if any(kw in query_lower for kw in ['news', 'latest', 'breaking']):
        agent_types.append(AgentType.NEWS)
    if any(kw in query_lower for kw in ['research', 'papers', 'academic']):
        agent_types.append(AgentType.ACADEMIC)
    # ... more detection logic

    return agent_types or [AgentType.GENERAL]
```

#### 3. Template-Based Decomposition

Use predefined templates for common workflows:

```python
async def decompose_task(self, task: str, context: Optional[Dict] = None) -> List[SubTask]:
    """Template-based decomposition for content creation."""

    # Content creation template
    template_tasks = [
        {"description": f"Research background on: {task}", "priority": 0},
        {"description": f"Identify key themes in: {task}", "priority": 1},
        {"description": f"Find supporting examples for: {task}", "priority": 2},
        {"description": f"Gather statistics/data on: {task}", "priority": 2},
        {"description": f"Create outline for: {task}", "priority": 3, "dependencies": ["task-0", "task-1"]},
        {"description": f"Draft content for: {task}", "priority": 4, "dependencies": ["task-4"]},
        {"description": f"Find visual assets for: {task}", "priority": 3},
    ]

    return [
        SubTask(
            id=f"task-{i}",
            description=st['description'],
            context=context or {},
            agent_type=AgentType.RESEARCH,
            priority=st['priority'],
            dependencies=st.get('dependencies', [])
        )
        for i, st in enumerate(template_tasks)
    ]
```

### Execution Strategies

#### 1. Simple Agent Execution

Direct LLM call for each subtask:

```python
async def execute_subtask(
    self,
    subtask: SubTask,
    context: Optional[Dict] = None
) -> AgentResult:
    """Simple LLM-based execution."""

    from llm_providers.xai_provider import XAIProvider
    import time

    provider = XAIProvider()
    start_time = time.time()

    try:
        response = await provider.generate(
            model=self.config.agent_model,
            messages=[
                {"role": "system", "content": "You are a research specialist."},
                {"role": "user", "content": subtask.description}
            ],
            timeout=self.config.timeout_seconds
        )

        return AgentResult(
            agent_id=subtask.id,
            agent_type=subtask.agent_type,
            status='success',
            result=response['content'],
            tokens_used=response.get('tokens_used', 0),
            cost=response.get('cost', 0.0),
            execution_time=time.time() - start_time,
            metadata={'model': self.config.agent_model}
        )

    except asyncio.TimeoutError:
        return AgentResult(
            agent_id=subtask.id,
            agent_type=subtask.agent_type,
            status='timeout',
            result="",
            error=f"Timeout after {self.config.timeout_seconds}s",
            tokens_used=0,
            cost=0.0,
            execution_time=time.time() - start_time,
            metadata={}
        )

    except Exception as e:
        return AgentResult(
            agent_id=subtask.id,
            agent_type=subtask.agent_type,
            status='failed',
            result="",
            error=str(e),
            tokens_used=0,
            cost=0.0,
            execution_time=time.time() - start_time,
            metadata={}
        )
```

#### 2. Multi-Provider Execution

Use different LLM providers based on agent type:

```python
async def execute_subtask(
    self,
    subtask: SubTask,
    context: Optional[Dict] = None
) -> AgentResult:
    """Multi-provider execution."""

    # Select provider based on agent type
    if subtask.agent_type == AgentType.ACADEMIC:
        from llm_providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        model = "claude-sonnet-4.5"  # Better for academic content
    elif subtask.agent_type == AgentType.TECHNICAL:
        from llm_providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        model = "gpt-4"  # Better for code
    else:
        from llm_providers.xai_provider import XAIProvider
        provider = XAIProvider()
        model = "grok-4-fast"  # General purpose

    # Execute with selected provider
    response = await provider.generate(
        model=model,
        messages=[{"role": "user", "content": subtask.description}]
    )

    return AgentResult(
        agent_id=subtask.id,
        agent_type=subtask.agent_type,
        status='success',
        result=response['content'],
        tokens_used=response.get('tokens_used', 0),
        cost=response.get('cost', 0.0),
        execution_time=0,
        metadata={'provider': provider.__class__.__name__, 'model': model}
    )
```

#### 3. Tool-Augmented Execution

Give agents access to tools (search, calculator, etc.):

```python
async def execute_subtask(
    self,
    subtask: SubTask,
    context: Optional[Dict] = None
) -> AgentResult:
    """Execution with tool access."""

    from llm_providers.xai_provider import XAIProvider
    provider = XAIProvider()

    # Define available tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            }
        }
    ]

    # Execute with tools
    response = await provider.generate(
        model="grok-3",
        messages=[{"role": "user", "content": subtask.description}],
        tools=tools
    )

    # Handle tool calls if present
    if response.get('tool_calls'):
        for tool_call in response['tool_calls']:
            if tool_call['name'] == 'web_search':
                search_results = await self._web_search(tool_call['arguments']['query'])
                # Feed results back to LLM
                # ...

    return AgentResult(...)
```

### Synthesis Strategies

#### 1. Single-Stage Synthesis

Combine all results in one LLM call:

```python
async def synthesize_results(
    self,
    agent_results: List[AgentResult],
    context: Optional[Dict] = None
) -> str:
    """Single-stage synthesis."""

    from llm_providers.xai_provider import XAIProvider
    provider = XAIProvider()

    # Filter successful results
    successful = [r for r in agent_results if r.status == 'success']

    # Combine findings
    combined = "\n\n---\n\n".join([
        f"## Agent {i+1}: {r.agent_id}\n\n{r.result}"
        for i, r in enumerate(successful)
    ])

    # Synthesize
    prompt = f"""Synthesize these research findings into a comprehensive report:

{combined}

Create a structured report with:
1. Executive Summary
2. Key Findings (organized by theme)
3. Detailed Analysis
4. Conclusions and Recommendations

Format in Markdown with proper headers and formatting."""

    response = await provider.generate(
        model=self.config.primary_model,
        messages=[{"role": "user", "content": prompt}]
    )

    return response['content']
```

#### 2. Hierarchical Synthesis (Beltalowda Pattern)

Multi-level synthesis for large agent counts:

```python
async def synthesize_results(
    self,
    agent_results: List[AgentResult],
    context: Optional[Dict] = None
) -> str:
    """Hierarchical synthesis: Level 1 → Level 2 → Executive."""

    from llm_providers.xai_provider import XAIProvider
    provider = XAIProvider()

    successful = [r for r in agent_results if r.status == 'success']

    # Level 1: Group agents and create mid-level syntheses
    group_size = self.config.synthesis_group_size  # e.g., 5
    groups = [successful[i:i+group_size] for i in range(0, len(successful), group_size)]

    level1_syntheses = []
    for i, group in enumerate(groups):
        combined = "\n\n".join([r.result for r in group])
        prompt = f"Synthesize these {len(group)} research findings into a cohesive summary:\n\n{combined}"

        response = await provider.generate(
            model=self.config.primary_model,
            messages=[{"role": "user", "content": prompt}]
        )

        level1_syntheses.append(response['content'])
        self._emit_event('synthesis_completed', {
            'level': 'mid',
            'group': i,
            'group_size': len(group)
        })

    # Level 2: Synthesize mid-level syntheses into final report
    if len(level1_syntheses) == 1:
        return level1_syntheses[0]

    combined_level1 = "\n\n---\n\n".join([
        f"## Section {i+1}\n\n{s}"
        for i, s in enumerate(level1_syntheses)
    ])

    prompt = f"""Create final comprehensive report from these section summaries:

{combined_level1}

Produce a unified narrative with:
1. Executive Summary
2. Key Findings (synthesized across all sections)
3. Detailed Analysis
4. Conclusions

Format in Markdown."""

    response = await provider.generate(
        model=self.config.primary_model,
        messages=[{"role": "user", "content": prompt}]
    )

    return response['content']
```

#### 3. Iterative Refinement Synthesis

Multiple passes to refine output:

```python
async def synthesize_results(
    self,
    agent_results: List[AgentResult],
    context: Optional[Dict] = None
) -> str:
    """Iterative refinement synthesis."""

    from llm_providers.xai_provider import XAIProvider
    provider = XAIProvider()

    successful = [r for r in agent_results if r.status == 'success']
    combined = "\n\n".join([r.result for r in successful])

    # Pass 1: Initial synthesis
    draft = await provider.generate(
        model=self.config.primary_model,
        messages=[{
            "role": "user",
            "content": f"Synthesize these findings into a report:\n\n{combined}"
        }]
    )

    # Pass 2: Critical review
    critique = await provider.generate(
        model=self.config.primary_model,
        messages=[
            {"role": "user", "content": f"Review this report and identify gaps, inconsistencies, or areas for improvement:\n\n{draft['content']}"}
        ]
    )

    # Pass 3: Refined synthesis
    final = await provider.generate(
        model=self.config.primary_model,
        messages=[
            {"role": "user", "content": f"Original findings:\n{combined}\n\nDraft report:\n{draft['content']}\n\nCritique:\n{critique['content']}\n\nCreate improved final report addressing the critique."}
        ]
    )

    return final['content']
```

## Best Practices

### 1. Prompting Best Practices

**Be specific in decomposition prompts:**
```python
# ❌ Vague
prompt = f"Break down: {task}"

# ✅ Specific
prompt = f"""Break down this task into {self.config.num_agents} specific, actionable subtasks.

Task: {task}

Each subtask should:
- Be independently executable
- Have clear deliverables
- Take 1-3 minutes to complete
- Require only LLM capabilities (no external APIs unless specified)

Return JSON array with descriptions and priorities."""
```

**Provide context in execution prompts:**
```python
# ❌ Minimal context
prompt = subtask.description

# ✅ Rich context
prompt = f"""You are a specialized research agent working on a larger project.

Overall Project: {context.get('original_task')}
Your Specific Task: {subtask.description}
Your Specialization: {subtask.specialization or 'General research'}

Requirements:
- Provide comprehensive, well-sourced findings
- Focus on factual accuracy
- Cite sources when possible
- Structure your response clearly

Execute this task now."""
```

### 2. Error Handling

**Always wrap LLM calls in try/except:**
```python
async def execute_subtask(self, subtask, context):
    start_time = time.time()

    try:
        response = await self.provider.generate(...)

        return AgentResult(
            agent_id=subtask.id,
            status='success',
            result=response['content'],
            ...
        )

    except asyncio.TimeoutError:
        # Specific handling for timeout
        self._emit_event('agent_timeout', {
            'agent_id': subtask.id,
            'timeout': self.config.timeout_seconds
        })

        return AgentResult(
            agent_id=subtask.id,
            status='timeout',
            error=f"Timeout after {self.config.timeout_seconds}s",
            ...
        )

    except Exception as e:
        # Generic error handling
        logger.exception(f"Agent {subtask.id} failed: {e}")

        return AgentResult(
            agent_id=subtask.id,
            status='failed',
            error=str(e),
            ...
        )
```

**Implement retry logic for transient failures:**
```python
from orchestration.utils import retry_async

async def execute_subtask(self, subtask, context):
    async def _execute():
        return await self.provider.generate(...)

    # Retry up to 3 times with exponential backoff
    response = await retry_async(
        _execute,
        max_retries=3,
        backoff=2.0,
        exceptions=(ConnectionError, TimeoutError)
    )

    return AgentResult(...)
```

### 3. Cost Optimization

**Use cheaper models for simple tasks:**
```python
def _select_model(self, subtask: SubTask) -> str:
    """Select model based on task complexity."""

    # Simple factual lookups: fast/cheap model
    if 'define' in subtask.description.lower() or 'what is' in subtask.description.lower():
        return "grok-4-fast"

    # Complex analysis: high-quality model
    if any(kw in subtask.description.lower() for kw in ['analyze', 'synthesize', 'compare']):
        return "grok-3"

    # Default
    return self.config.agent_model
```

**Track and limit costs:**
```python
from orchestration.utils import CostTracker

class MyOrchestrator(BaseOrchestrator):
    def __init__(self, config):
        super().__init__(config)
        self.cost_tracker = CostTracker(
            max_cost=10.0,  # Abort if cost exceeds $10
            warn_threshold=5.0  # Warn at $5
        )

    async def execute_subtask(self, subtask, context):
        result = await super().execute_subtask(subtask, context)

        # Track cost
        self.cost_tracker.add_cost(result.cost)

        if self.cost_tracker.total_cost > self.cost_tracker.max_cost:
            raise Exception(f"Cost limit exceeded: ${self.cost_tracker.total_cost:.2f}")

        return result
```

### 4. Performance Optimization

**Optimize parallel execution:**
```python
# Configure for optimal parallelism
config = MyOrchestratorConfig(
    parallel_execution=True,
    max_concurrent_agents=10,  # Balance speed vs rate limits
    timeout_seconds=120  # Prevent hanging agents
)
```

**Use streaming for large outputs:**
```python
async def execute_subtask(self, subtask, context):
    """Stream agent output for large responses."""

    response_chunks = []

    async for chunk in self.provider.generate_stream(
        model=self.config.agent_model,
        messages=[{"role": "user", "content": subtask.description}]
    ):
        response_chunks.append(chunk)

        # Emit progress events
        self._emit_event('agent_progress', {
            'agent_id': subtask.id,
            'progress': len(response_chunks) / estimated_total,
            'current_output': ''.join(response_chunks)
        })

    return AgentResult(
        result=''.join(response_chunks),
        ...
    )
```

### 5. Testing Strategies

**Unit test each method independently:**
```python
import pytest
from orchestration.my_orchestrator import MyOrchestrator

@pytest.mark.asyncio
async def test_decompose_task():
    orchestrator = MyOrchestrator()

    subtasks = await orchestrator.decompose_task(
        task="Research quantum computing applications",
        context={}
    )

    assert len(subtasks) > 0
    assert all(isinstance(st, SubTask) for st in subtasks)
    assert all(st.description for st in subtasks)

@pytest.mark.asyncio
async def test_execute_subtask():
    orchestrator = MyOrchestrator()

    subtask = SubTask(
        id="test-1",
        description="Define quantum computing",
        context={},
        agent_type=AgentType.RESEARCH,
        priority=0,
        dependencies=[]
    )

    result = await orchestrator.execute_subtask(subtask)

    assert result.status == 'success'
    assert len(result.result) > 0
    assert result.cost >= 0
```

**Integration test full workflows:**
```python
@pytest.mark.asyncio
async def test_full_workflow():
    orchestrator = MyOrchestrator(MyOrchestratorConfig(
        num_agents=3,
        generate_documents=False  # Faster testing
    ))

    result = await orchestrator.execute_workflow(
        task="Quick research on transformers",
        title="Test Workflow"
    )

    assert result.status == TaskStatus.COMPLETED
    assert len(result.agent_results) == 3
    assert result.final_synthesis is not None
```

## Advanced Patterns

### Pattern 1: Conditional Execution

Execute subtasks based on previous results:

```python
async def execute_workflow(self, task, title, context, stream_callback):
    """Override to add conditional execution logic."""

    # Initial decomposition
    subtasks = await self.decompose_task(task, context)

    # Execute first phase
    phase1_results = await self._execute_agents_parallel(subtasks[:3], context)

    # Decide next steps based on phase 1 results
    if self._should_deep_dive(phase1_results):
        # Create additional subtasks for deep dive
        phase2_subtasks = await self._create_deep_dive_tasks(phase1_results)
        phase2_results = await self._execute_agents_parallel(phase2_subtasks, context)
        all_results = phase1_results + phase2_results
    else:
        all_results = phase1_results

    # Continue with synthesis
    final_synthesis = await self.synthesize_results(all_results, context)
    ...
```

### Pattern 2: Human-in-the-Loop

Pause for human review between stages:

```python
async def synthesize_results(self, agent_results, context):
    """Pause for human review before final synthesis."""

    # Draft synthesis
    draft = await self._create_draft_synthesis(agent_results)

    # Emit event for human review
    self._emit_event('review_required', {
        'draft': draft,
        'agent_count': len(agent_results)
    })

    # Wait for human feedback (via webhook or polling)
    feedback = await self._wait_for_human_feedback(timeout=3600)  # 1 hour

    if feedback.get('approved'):
        return draft
    else:
        # Incorporate feedback and regenerate
        return await self._regenerate_with_feedback(draft, feedback)
```

### Pattern 3: Multi-Modal Synthesis

Combine text, images, and data:

```python
async def synthesize_results(self, agent_results, context):
    """Multi-modal synthesis with visualizations."""

    # Text synthesis
    text_report = await self._synthesize_text(agent_results)

    # Generate visualizations
    charts = await self._generate_charts(agent_results)

    # Generate infographics
    infographics = await self._generate_infographics(text_report)

    # Combine into final multi-modal report
    return {
        'text': text_report,
        'visualizations': charts,
        'infographics': infographics
    }
```

### Pattern 4: SequentialOrchestrator (out-of-the-box)

```python
from shared.orchestration import OrchestratorConfig, SequentialOrchestrator, AgentType

config = OrchestratorConfig(
    parallel_execution=False,
    generate_documents=False,
)

orchestrator = SequentialOrchestrator(config)
result = await orchestrator.execute_workflow(
    task="Produce audience briefing",
    context={
        "steps": [
            {
                "id": "research",
                "description": "Collect supporting evidence",
                "agent_type": AgentType.WORKER,
                "handler": lambda subtask, ctx: "curated research notes",
            },
            {
                "id": "summary",
                "description": "Summarize for executives",
                "agent_type": AgentType.SYNTHESIZER,
                "handler": lambda subtask, ctx: "executive-ready summary",
            },
        ]
    },
)
```

### Pattern 5: ConditionalOrchestrator (out-of-the-box)

```python
from shared.orchestration import ConditionalOrchestrator

context = {
    "condition": "remediation",
    "branches": {
        "assessment": [{"description": "Run risk assessment"}],
        "remediation": [{"description": "Generate mitigation playbook"}],
    },
}

orchestrator = ConditionalOrchestrator(OrchestratorConfig())
result = await orchestrator.execute_workflow("Security incident response", context=context)
```

### Pattern 6: IterativeOrchestrator (out-of-the-box)

```python
from shared.orchestration import IterativeOrchestrator

context = {
    "max_iterations": 3,
    "success_predicate": lambda synthesis, *_: "refined" in synthesis,
}

orchestrator = IterativeOrchestrator(OrchestratorConfig())
result = await orchestrator.execute_workflow("Refine launch brief", context=context)
```

## Testing and Debugging

### Debugging Tips

**Enable verbose logging:**
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

**Add debug events:**
```python
async def execute_subtask(self, subtask, context):
    self._emit_event('debug', {
        'message': f"Executing subtask: {subtask.id}",
        'subtask': subtask.__dict__
    })

    result = await ...

    self._emit_event('debug', {
        'message': f"Completed subtask: {subtask.id}",
        'result_preview': result.result[:100]
    })

    return result
```

**Test with minimal configuration:**
```python
# Fast iteration during development
test_config = MyOrchestratorConfig(
    num_agents=2,  # Minimal agent count
    generate_documents=False,  # Skip document generation
    timeout_seconds=30,  # Short timeout
    agent_model="grok-4-fast"  # Cheapest model
)

orchestrator = MyOrchestrator(test_config)
```

## Deployment

### Production Configuration

```python
production_config = MyOrchestratorConfig(
    num_agents=10,
    parallel_execution=True,
    max_concurrent_agents=10,
    timeout_seconds=180,
    retry_failed_tasks=True,
    max_retries=2,
    generate_documents=True,
    document_formats=["pdf", "docx", "markdown"],
    primary_model="grok-3",
    agent_model="grok-4-fast"
)
```

### Monitoring

**Track key metrics:**
```python
class MyOrchestrator(BaseOrchestrator):
    async def execute_workflow(self, task, title, context, stream_callback):
        start_time = time.time()

        result = await super().execute_workflow(task, title, context, stream_callback)

        # Log metrics
        logger.info(f"Workflow {self.task_id} completed", extra={
            'task_id': self.task_id,
            'duration': time.time() - start_time,
            'total_cost': result.total_cost,
            'num_agents': len(result.agent_results),
            'success_rate': len([r for r in result.agent_results if r.status == 'success']) / len(result.agent_results)
        })

        return result
```

---

**Author:** Luke Steuber
**Last Updated:** 2025-11-15
**Version:** 1.0.0

**Next Steps:**
1. Review the [orchestrator template](/home/coolhand/shared/orchestration/templates/orchestrator_template.py)
2. Check [Beltalowda](/home/coolhand/shared/orchestration/beltalowda_orchestrator.py) and [Swarm](/home/coolhand/shared/orchestration/swarm_orchestrator.py) implementations
3. Build your custom orchestrator
4. Test locally
5. Deploy to MCP server
