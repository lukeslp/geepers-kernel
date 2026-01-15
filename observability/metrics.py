"""
Metrics Collection for Shared Library

Prometheus-compatible metrics for monitoring tool usage, provider calls,
orchestrator workflows, and cache operations.

Author: Luke Steuber
"""

import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict
from threading import Lock
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Counter:
    """Simple counter metric."""
    value: int = 0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def inc(self, amount: int = 1):
        """Increment counter."""
        self.value += amount


@dataclass
class Histogram:
    """Histogram for tracking distributions."""
    values: list = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def observe(self, value: float):
        """Record a value."""
        self.values.append(value)
    
    def get_percentile(self, percentile: float) -> float:
        """Get percentile value (e.g., 0.95 for p95)."""
        if not self.values:
            return 0.0
        sorted_values = sorted(self.values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_average(self) -> float:
        """Get average value."""
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)


@dataclass
class Gauge:
    """Gauge metric for values that go up and down."""
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def set(self, value: float):
        """Set gauge value."""
        self.value = value
    
    def inc(self, amount: float = 1.0):
        """Increment gauge."""
        self.value += amount
    
    def dec(self, amount: float = 1.0):
        """Decrement gauge."""
        self.value -= amount


class MetricsCollector:
    """
    Centralized metrics collection for shared library.
    
    Tracks:
    - Tool invocations (count, duration, errors)
    - Provider API calls (count, duration, cost, tokens)
    - Orchestrator workflows (count, duration, agent count, cost)
    - Cache operations (hits, misses, operations)
    
    Usage:
        from shared.observability import get_metrics_collector
        
        metrics = get_metrics_collector()
        
        # Track tool call
        with metrics.track_tool_call('arxiv_search'):
            results = search_arxiv(query)
        
        # Track provider call
        metrics.record_provider_call(
            provider='openai',
            model='gpt-4o',
            prompt_tokens=100,
            completion_tokens=50,
            duration=1.5
        )
    """
    
    _instance = None
    _lock = Lock()
    
    def __init__(self):
        """Initialize metrics collector."""
        # Tool metrics
        self.tool_calls_total = defaultdict(lambda: Counter())
        self.tool_duration = defaultdict(lambda: Histogram())
        self.tool_errors = defaultdict(lambda: Counter())
        
        # Provider metrics
        self.provider_calls_total = defaultdict(lambda: Counter())
        self.provider_duration = defaultdict(lambda: Histogram())
        self.provider_cost = defaultdict(lambda: Counter())
        self.provider_tokens = defaultdict(lambda: Counter())
        
        # Orchestrator metrics
        self.orchestrator_workflows = defaultdict(lambda: Counter())
        self.orchestrator_duration = defaultdict(lambda: Histogram())
        self.orchestrator_agent_count = defaultdict(lambda: Histogram())
        self.orchestrator_cost = defaultdict(lambda: Counter())
        
        # Cache metrics
        self.cache_operations = defaultdict(lambda: Counter())
        self.cache_hit_rate = Gauge()
        self.cache_memory_bytes = Gauge()
        
        # Active workflows gauge
        self.active_workflows = Gauge()
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def track_tool_call(self, tool_name: str, provider: Optional[str] = None):
        """
        Context manager for tracking tool calls.
        
        Usage:
            with metrics.track_tool_call('arxiv_search'):
                results = search_arxiv(query)
        """
        return ToolCallContext(self, tool_name, provider)
    
    def record_tool_call(
        self,
        tool_name: str,
        duration: float,
        success: bool = True,
        provider: Optional[str] = None
    ):
        """
        Record a tool call.
        
        Args:
            tool_name: Name of the tool
            duration: Duration in seconds
            success: Whether the call succeeded
            provider: Optional provider name
        """
        key = (tool_name, provider or 'none')
        self.tool_calls_total[key].inc()
        self.tool_duration[key].observe(duration)
        
        if not success:
            self.tool_errors[key].inc()
        
        logger.debug(f"Tool call: {tool_name} ({duration:.3f}s, success={success})")
    
    def record_provider_call(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration: float,
        cost_usd: Optional[float] = None
    ):
        """
        Record a provider API call.
        
        Args:
            provider: Provider name
            model: Model name
            prompt_tokens: Tokens in prompt
            completion_tokens: Tokens in completion
            duration: Duration in seconds
            cost_usd: Cost in USD (if known)
        """
        key = (provider, model)
        self.provider_calls_total[key].inc()
        self.provider_duration[key].observe(duration)
        self.provider_tokens[key].inc(prompt_tokens + completion_tokens)
        
        if cost_usd:
            self.provider_cost[key].inc(int(cost_usd * 1000000))  # Store as micro-dollars
        
        logger.debug(
            f"Provider call: {provider}/{model} "
            f"({prompt_tokens}+{completion_tokens} tokens, {duration:.3f}s)"
        )
    
    def record_orchestrator_workflow(
        self,
        orchestrator_type: str,
        duration: float,
        agent_count: int,
        cost_usd: float,
        success: bool = True
    ):
        """
        Record an orchestrator workflow.
        
        Args:
            orchestrator_type: Type of orchestrator
            duration: Duration in seconds
            agent_count: Number of agents used
            cost_usd: Total cost in USD
            success: Whether workflow succeeded
        """
        key = (orchestrator_type, 'completed' if success else 'failed')
        self.orchestrator_workflows[key].inc()
        self.orchestrator_duration[orchestrator_type].observe(duration)
        self.orchestrator_agent_count[orchestrator_type].observe(agent_count)
        self.orchestrator_cost[orchestrator_type].inc(int(cost_usd * 1000000))
        
        logger.info(
            f"Orchestrator workflow: {orchestrator_type} "
            f"({agent_count} agents, {duration:.1f}s, ${cost_usd:.4f})"
        )
    
    def record_cache_operation(
        self,
        operation: str,  # get, set, delete
        hit: Optional[bool] = None,  # True if cache hit (for get operations)
        namespace: str = 'default'
    ):
        """
        Record a cache operation.
        
        Args:
            operation: Operation type (get, set, delete)
            hit: Whether operation was a cache hit (for get)
            namespace: Cache namespace
        """
        key = (operation, namespace)
        self.cache_operations[key].inc()
        
        if operation == 'get' and hit is not None:
            # Update hit rate (simple moving average)
            total_key = ('get', namespace)
            total = self.cache_operations[total_key].value
            if total > 0:
                hits = sum(
                    count.value for (op, ns), count in self.cache_operations.items()
                    if op == 'get' and ns == namespace and hit
                )
                hit_rate = hits / total
                self.cache_hit_rate.set(hit_rate)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current statistics.
        
        Returns:
            Dict with all metrics
        """
        return {
            'tools': {
                'total_calls': sum(c.value for c in self.tool_calls_total.values()),
                'total_errors': sum(c.value for c in self.tool_errors.values()),
                'by_tool': {
                    f"{tool}/{provider}": {
                        'calls': self.tool_calls_total[(tool, provider)].value,
                        'errors': self.tool_errors[(tool, provider)].value,
                        'avg_duration': self.tool_duration[(tool, provider)].get_average(),
                        'p95_duration': self.tool_duration[(tool, provider)].get_percentile(0.95)
                    }
                    for (tool, provider) in self.tool_calls_total.keys()
                }
            },
            'providers': {
                'total_calls': sum(c.value for c in self.provider_calls_total.values()),
                'total_tokens': sum(c.value for c in self.provider_tokens.values()),
                'total_cost_usd': sum(c.value for c in self.provider_cost.values()) / 1000000,
                'by_provider': {
                    f"{provider}/{model}": {
                        'calls': self.provider_calls_total[(provider, model)].value,
                        'tokens': self.provider_tokens[(provider, model)].value,
                        'cost_usd': self.provider_cost[(provider, model)].value / 1000000,
                        'avg_duration': self.provider_duration[(provider, model)].get_average()
                    }
                    for (provider, model) in self.provider_calls_total.keys()
                }
            },
            'orchestrators': {
                'total_workflows': sum(c.value for c in self.orchestrator_workflows.values()),
                'active_workflows': int(self.active_workflows.value),
                'by_type': {
                    orch_type: {
                        'workflows': sum(
                            c.value for (ot, status), c in self.orchestrator_workflows.items()
                            if ot == orch_type
                        ),
                        'avg_duration': self.orchestrator_duration[orch_type].get_average(),
                        'avg_agents': self.orchestrator_agent_count[orch_type].get_average(),
                        'total_cost_usd': self.orchestrator_cost[orch_type].value / 1000000
                    }
                    for orch_type in set(ot for (ot, _) in self.orchestrator_workflows.keys())
                }
            },
            'cache': {
                'hit_rate': self.cache_hit_rate.value,
                'memory_bytes': int(self.cache_memory_bytes.value),
                'operations': {
                    f"{op}/{ns}": self.cache_operations[(op, ns)].value
                    for (op, ns) in self.cache_operations.keys()
                }
            }
        }
    
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        
        # Tool metrics
        for (tool, provider), counter in self.tool_calls_total.items():
            lines.append(
                f'tool_calls_total{{tool="{tool}",provider="{provider}"}} {counter.value}'
            )
        
        # Provider metrics
        for (provider, model), counter in self.provider_calls_total.items():
            lines.append(
                f'provider_calls_total{{provider="{provider}",model="{model}"}} {counter.value}'
            )
            lines.append(
                f'provider_tokens_total{{provider="{provider}",model="{model}"}} '
                f'{self.provider_tokens[(provider, model)].value}'
            )
        
        # Orchestrator metrics
        lines.append(f'orchestrator_active_workflows {int(self.active_workflows.value)}')
        
        # Cache metrics
        lines.append(f'cache_hit_rate {self.cache_hit_rate.value}')
        lines.append(f'cache_memory_bytes {int(self.cache_memory_bytes.value)}')
        
        return '\n'.join(lines) + '\n'


class ToolCallContext:
    """Context manager for tracking tool calls."""
    
    def __init__(self, collector: MetricsCollector, tool_name: str, provider: Optional[str] = None):
        self.collector = collector
        self.tool_name = tool_name
        self.provider = provider
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.success = exc_type is None
        self.collector.record_tool_call(
            self.tool_name,
            duration,
            self.success,
            self.provider
        )
        return False  # Don't suppress exceptions


# Convenience function
def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return MetricsCollector.get_instance()
