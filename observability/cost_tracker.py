"""
Cost Tracking for LLM Provider Calls

Real-time cost calculation and budget monitoring across all providers.

Author: Luke Steuber
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime, date
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _load_pricing() -> Dict:
    """Load pricing from pricing.yaml, converting floats to Decimal.

    Note: Decimal(str(v)) avoids floating-point representation errors
    that would occur with Decimal(v) directly on YAML-parsed floats.
    """
    pricing_file = Path(__file__).parent / "pricing.yaml"
    try:
        with open(pricing_file) as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"pricing.yaml not found at {pricing_file}. "
            "Ensure the package was installed with its data files."
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse pricing.yaml: {e}")

    if not isinstance(raw, dict):
        raise ValueError(f"pricing.yaml must be a mapping, got {type(raw).__name__}")

    try:
        return {
            provider: {
                model: {
                    k: Decimal(str(v)) for k, v in rates.items()
                }
                for model, rates in models.items()
            }
            for provider, models in raw.items()
        }
    except (AttributeError, TypeError) as e:
        raise ValueError(
            f"pricing.yaml has unexpected structure. "
            "Expected: provider -> model -> {{prompt: float, completion: float}}. "
            f"Error: {e}"
        )


PRICING = _load_pricing()


@dataclass
class Cost:
    """Individual cost entry."""
    timestamp: datetime
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    metadata: Dict = field(default_factory=dict)


@dataclass
class CostBreakdown:
    """Cost breakdown for a workflow or time period."""
    total_cost: Decimal
    by_provider: Dict[str, Decimal]
    by_model: Dict[str, Decimal]
    total_tokens: int
    call_count: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class CostTracker:
    """
    Real-time cost tracking across all providers.
    
    Usage:
        from shared.observability import get_cost_tracker
        
        tracker = get_cost_tracker()
        
        # Calculate cost for a call
        cost = tracker.calculate_cost(
            provider='openai',
            model='gpt-4o',
            prompt_tokens=100,
            completion_tokens=50
        )
        
        # Track workflow cost
        workflow_id = 'research-001'
        tracker.track_workflow_cost(workflow_id, cost)
        
        # Get daily costs
        today_costs = tracker.get_daily_costs(date.today())
    """
    
    _instance = None
    
    def __init__(self):
        """Initialize cost tracker."""
        self.workflow_costs = defaultdict(list)  # workflow_id -> List[Cost]
        self.daily_costs = defaultdict(list)  # date -> List[Cost]
        self.provider_costs = defaultdict(Decimal)  # provider -> total_cost
        self.model_costs = defaultdict(Decimal)  # model -> total_cost
        self.total_cost = Decimal('0')
        self.budget_alerts = {}  # daily_limit -> webhook_url
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def calculate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> Decimal:
        """
        Calculate cost for an LLM call.
        
        Args:
            provider: Provider name
            model: Model name
            prompt_tokens: Tokens in prompt
            completion_tokens: Tokens in completion
        
        Returns:
            Cost in USD
        """
        provider_lower = provider.lower()
        
        if provider_lower not in PRICING:
            logger.warning(f"No pricing data for provider: {provider}")
            return Decimal('0')
        
        if model not in PRICING[provider_lower]:
            logger.warning(f"No pricing data for model: {provider}/{model}")
            return Decimal('0')
        
        pricing = PRICING[provider_lower][model]
        
        # Cost = (prompt_tokens / 1M * prompt_price) + (completion_tokens / 1M * completion_price)
        prompt_cost = (Decimal(prompt_tokens) / Decimal('1000000')) * pricing['prompt']
        completion_cost = (Decimal(completion_tokens) / Decimal('1000000')) * pricing['completion']
        
        total_cost = prompt_cost + completion_cost
        
        logger.debug(
            f"Cost calculation: {provider}/{model} "
            f"({prompt_tokens}+{completion_tokens} tokens) = ${total_cost:.6f}"
        )
        
        return total_cost
    
    def track_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        workflow_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Cost:
        """
        Track a cost entry.
        
        Args:
            provider: Provider name
            model: Model name
            prompt_tokens: Tokens in prompt
            completion_tokens: Tokens in completion
            workflow_id: Optional workflow identifier
            metadata: Optional metadata
        
        Returns:
            Cost object
        """
        cost_usd = self.calculate_cost(provider, model, prompt_tokens, completion_tokens)
        
        cost = Cost(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            metadata=metadata or {}
        )
        
        # Track by workflow
        if workflow_id:
            self.workflow_costs[workflow_id].append(cost)
        
        # Track by day
        today = date.today()
        self.daily_costs[today].append(cost)
        
        # Update totals
        self.provider_costs[provider] += cost_usd
        self.model_costs[model] += cost_usd
        self.total_cost += cost_usd
        
        # Check budget alerts
        self._check_budget_alerts(today)
        
        return cost
    
    def get_workflow_cost(self, workflow_id: str) -> CostBreakdown:
        """
        Get cost breakdown for a workflow.
        
        Args:
            workflow_id: Workflow identifier
        
        Returns:
            CostBreakdown object
        """
        costs = self.workflow_costs.get(workflow_id, [])
        
        if not costs:
            return CostBreakdown(
                total_cost=Decimal('0'),
                by_provider={},
                by_model={},
                total_tokens=0,
                call_count=0
            )
        
        by_provider = defaultdict(Decimal)
        by_model = defaultdict(Decimal)
        total_tokens = 0
        
        for cost in costs:
            by_provider[cost.provider] += cost.cost_usd
            by_model[cost.model] += cost.cost_usd
            total_tokens += cost.prompt_tokens + cost.completion_tokens
        
        return CostBreakdown(
            total_cost=sum(c.cost_usd for c in costs),
            by_provider=dict(by_provider),
            by_model=dict(by_model),
            total_tokens=total_tokens,
            call_count=len(costs),
            start_time=min(c.timestamp for c in costs),
            end_time=max(c.timestamp for c in costs)
        )
    
    def get_daily_costs(self, target_date: date) -> CostBreakdown:
        """
        Get cost breakdown for a specific day.
        
        Args:
            target_date: Date to query
        
        Returns:
            CostBreakdown object
        """
        costs = self.daily_costs.get(target_date, [])
        
        if not costs:
            return CostBreakdown(
                total_cost=Decimal('0'),
                by_provider={},
                by_model={},
                total_tokens=0,
                call_count=0
            )
        
        by_provider = defaultdict(Decimal)
        by_model = defaultdict(Decimal)
        total_tokens = 0
        
        for cost in costs:
            by_provider[cost.provider] += cost.cost_usd
            by_model[cost.model] += cost.cost_usd
            total_tokens += cost.prompt_tokens + cost.completion_tokens
        
        return CostBreakdown(
            total_cost=sum(c.cost_usd for c in costs),
            by_provider=dict(by_provider),
            by_model=dict(by_model),
            total_tokens=total_tokens,
            call_count=len(costs)
        )
    
    def set_budget_alert(
        self,
        daily_limit_usd: Decimal,
        webhook_url: str
    ):
        """
        Set a budget alert.
        
        Args:
            daily_limit_usd: Daily spending limit in USD
            webhook_url: Webhook URL to call when limit exceeded
        """
        self.budget_alerts[daily_limit_usd] = webhook_url
        logger.info(f"Budget alert set: ${daily_limit_usd}/day -> {webhook_url}")
    
    def _check_budget_alerts(self, target_date: date):
        """Check if any budget alerts should fire."""
        if not self.budget_alerts:
            return
        
        daily_total = sum(c.cost_usd for c in self.daily_costs.get(target_date, []))
        
        for limit, webhook_url in self.budget_alerts.items():
            if daily_total >= limit:
                logger.warning(
                    f"Budget alert: Daily spending ${daily_total:.2f} "
                    f"exceeded limit ${limit:.2f}"
                )
                # TODO: Implement webhook call
    
    def get_summary(self) -> Dict:
        """
        Get overall cost summary.
        
        Returns:
            Dict with cost statistics
        """
        return {
            'total_cost_usd': float(self.total_cost),
            'by_provider': {k: float(v) for k, v in self.provider_costs.items()},
            'by_model': {k: float(v) for k, v in self.model_costs.items()},
            'today': {
                'cost_usd': float(sum(
                    c.cost_usd for c in self.daily_costs.get(date.today(), [])
                )),
                'calls': len(self.daily_costs.get(date.today(), []))
            },
            'active_workflows': len(self.workflow_costs)
        }


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    return CostTracker.get_instance()
