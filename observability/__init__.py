"""
Observability Module for Shared Library

Provides metrics collection, cost tracking, and monitoring capabilities.

Usage:
    from shared.observability import get_metrics_collector, get_cost_tracker
    
    # Track tool usage
    metrics = get_metrics_collector()
    with metrics.track_tool_call('arxiv_search'):
        results = search_arxiv(query)
    
    # Track costs
    tracker = get_cost_tracker()
    cost = tracker.calculate_cost('openai', 'gpt-4o', 100, 50)

Author: Luke Steuber
"""

from .metrics import MetricsCollector, get_metrics_collector, ToolCallContext
from .cost_tracker import CostTracker, get_cost_tracker, Cost, CostBreakdown

__all__ = [
    'MetricsCollector',
    'get_metrics_collector',
    'ToolCallContext',
    'CostTracker',
    'get_cost_tracker',
    'Cost',
    'CostBreakdown',
]
