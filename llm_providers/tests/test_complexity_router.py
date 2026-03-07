"""
Tests for ComplexityRouter: complexity detection, budget adjustment,
routing decisions, fallback logic, and cost tracking.
"""

import pytest
from llm_providers.complexity_router import (
    ComplexityRouter, Complexity, BudgetTier, RoutingDecision,
)
from llm_providers import COMPLEXITY_TIERS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def router():
    return ComplexityRouter(default_provider="openai", default_budget=BudgetTier.BALANCED)


@pytest.fixture
def cheap_router():
    return ComplexityRouter(default_provider="openai", default_budget=BudgetTier.CHEAP)


@pytest.fixture
def premium_router():
    return ComplexityRouter(default_provider="openai", default_budget=BudgetTier.PREMIUM)


# ---------------------------------------------------------------------------
# Complexity detection
# ---------------------------------------------------------------------------

class TestComplexityDetection:
    def test_simple_keywords_give_simple(self, router):
        result = router._detect_complexity("What is Python?")
        assert result == Complexity.SIMPLE

    def test_very_short_query_is_simple(self, router):
        result = router._detect_complexity("Hello")
        assert result == Complexity.SIMPLE

    def test_complex_keyword_gives_complex(self, router):
        result = router._detect_complexity("Design a comprehensive microservices architecture")
        assert result == Complexity.COMPLEX

    def test_code_in_long_query_is_complex(self, router):
        query = "def my_func(x): return x * 2  # Can you refactor this function to be more efficient"
        result = router._detect_complexity(query)
        assert result == Complexity.COMPLEX

    def test_medium_keywords_give_medium(self, router):
        result = router._detect_complexity("Explain how HTTP works and describe the request lifecycle")
        assert result == Complexity.MEDIUM

    def test_multiple_questions_mark_complex(self, router):
        result = router._detect_complexity("What is Python? How does it work? Why is it popular?")
        assert result == Complexity.COMPLEX

    def test_long_query_without_keywords_defaults_to_medium_or_complex(self, router):
        long_query = "Please " + "analyze " * 10 + "this carefully"
        result = router._detect_complexity(long_query)
        assert result in (Complexity.MEDIUM, Complexity.COMPLEX)


# ---------------------------------------------------------------------------
# Budget adjustment
# ---------------------------------------------------------------------------

class TestBudgetAdjustment:
    def test_cheap_downgrades_medium_to_simple(self, router):
        result = router._adjust_for_budget(Complexity.MEDIUM, BudgetTier.CHEAP)
        assert result == "simple"

    def test_cheap_downgrades_complex_to_medium(self, router):
        result = router._adjust_for_budget(Complexity.COMPLEX, BudgetTier.CHEAP)
        assert result == "medium"

    def test_cheap_keeps_simple(self, router):
        result = router._adjust_for_budget(Complexity.SIMPLE, BudgetTier.CHEAP)
        assert result == "simple"

    def test_premium_upgrades_simple_to_medium(self, router):
        result = router._adjust_for_budget(Complexity.SIMPLE, BudgetTier.PREMIUM)
        assert result == "medium"

    def test_premium_keeps_medium(self, router):
        result = router._adjust_for_budget(Complexity.MEDIUM, BudgetTier.PREMIUM)
        assert result == "medium"

    def test_premium_keeps_complex(self, router):
        result = router._adjust_for_budget(Complexity.COMPLEX, BudgetTier.PREMIUM)
        assert result == "complex"

    def test_balanced_makes_no_change(self, router):
        for c in Complexity:
            assert router._adjust_for_budget(c, BudgetTier.BALANCED) == c.value


# ---------------------------------------------------------------------------
# Route method
# ---------------------------------------------------------------------------

class TestRoute:
    def test_returns_routing_decision(self, router):
        decision = router.route("What is Python?")
        assert isinstance(decision, RoutingDecision)

    def test_decision_has_correct_provider(self, router):
        decision = router.route("Hello", provider="anthropic")
        assert decision.provider == "anthropic"

    def test_decision_model_matches_complexity_tier(self, router):
        decision = router.route("What is Python?", provider="openai")
        assert decision.model in COMPLEXITY_TIERS["openai"].values()

    def test_unknown_provider_raises(self, router):
        with pytest.raises(ValueError, match="not supported"):
            router.route("Query", provider="banana")

    def test_decision_appended_to_history(self, router):
        router.route("What is Python?")
        assert len(router.routing_history) == 1

    def test_multiple_routes_build_history(self, router):
        for _ in range(5):
            router.route("Simple query: what is 1+1?")
        assert len(router.routing_history) == 5

    def test_defaults_used_when_no_args(self, router):
        decision = router.route("Hello world")
        assert decision.provider == "openai"
        assert decision.budget_tier == BudgetTier.BALANCED

    def test_capability_check_no_fallback_needed(self, router):
        """Routing with a capability the provider supports should have no fallback."""
        decision = router.route("Describe this image", provider="openai", require_capability="vision")
        assert decision.fallback_provider is None

    def test_capability_check_triggers_fallback(self, router):
        """Groq doesn't support image generation — we expect a fallback provider."""
        decision = router.route(
            "Generate an image of a cat",
            provider="groq",
            require_capability="image_generation"
        )
        assert decision.fallback_provider is not None
        assert decision.fallback_model is not None

    def test_nonexistent_capability_raises(self, router):
        with pytest.raises(ValueError, match="No providers support"):
            router.route("Query", provider="openai", require_capability="teleportation")


# ---------------------------------------------------------------------------
# Cost savings
# ---------------------------------------------------------------------------

class TestCostSavings:
    def test_no_history_returns_error(self, router):
        result = router.get_cost_savings()
        assert "error" in result

    def test_with_history_returns_stats(self, router):
        router.route("What is Python?")
        router.route("Define recursion")
        router.route("Design a comprehensive distributed system architecture")
        result = router.get_cost_savings()
        assert "total_queries" in result
        assert result["total_queries"] == 3
        assert "savings_percent" in result
        assert "simple_queries" in result
        assert "complex_queries" in result

    def test_savings_non_negative(self, router):
        router.route("Simple: what is 1+1?")
        result = router.get_cost_savings(compared_to_provider="openai")
        assert result["savings_percent"] >= 0


# ---------------------------------------------------------------------------
# explain_last_decision
# ---------------------------------------------------------------------------

class TestExplainLastDecision:
    def test_no_history_returns_message(self, router):
        result = router.explain_last_decision()
        assert "No routing decisions" in result

    def test_with_history_returns_explanation(self, router):
        router.route("What is Python?")
        result = router.explain_last_decision()
        assert "Provider" in result
        assert "Model" in result
        assert "Complexity" in result

    def test_explanation_includes_fallback_when_present(self, router):
        router.route(
            "Generate an image",
            provider="groq",
            require_capability="image_generation"
        )
        result = router.explain_last_decision()
        assert "Fallback" in result


# ---------------------------------------------------------------------------
# Complexity and BudgetTier enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_complexity_values(self):
        assert Complexity.SIMPLE.value == "simple"
        assert Complexity.MEDIUM.value == "medium"
        assert Complexity.COMPLEX.value == "complex"

    def test_budget_tier_values(self):
        assert BudgetTier.CHEAP.value == "cheap"
        assert BudgetTier.BALANCED.value == "balanced"
        assert BudgetTier.PREMIUM.value == "premium"

    def test_routing_decision_is_dataclass(self):
        decision = RoutingDecision(
            provider="openai",
            model="gpt-4o-mini",
            complexity=Complexity.SIMPLE,
            budget_tier=BudgetTier.CHEAP,
            estimated_cost_multiplier=1.0,
            reason="Test reason",
        )
        assert decision.fallback_provider is None
        assert decision.fallback_model is None
