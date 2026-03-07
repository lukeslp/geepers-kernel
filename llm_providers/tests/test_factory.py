"""
Tests for ProviderFactory: get_provider, create_provider, caching,
capability matrix, complexity routing, and error handling.

All provider SDK imports are mocked — no real API calls are made.
"""

import pytest
from unittest.mock import MagicMock, patch
from llm_providers import ProviderFactory, PROVIDER_CAPABILITIES, COMPLEXITY_TIERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_PROVIDERS = [
    "anthropic", "openai", "ollama", "mistral",
    "cohere", "gemini", "perplexity", "huggingface", "groq",
]


def _make_anthropic_mock():
    """Return a mock that satisfies AnthropicProvider.__init__."""
    mock_client = MagicMock()
    mock_anthropic_module = MagicMock()
    mock_anthropic_module.Anthropic.return_value = mock_client
    return mock_anthropic_module


def _make_openai_mock():
    mock_client = MagicMock()
    mock_openai_module = MagicMock()
    mock_openai_module.OpenAI.return_value = mock_client
    return mock_openai_module


# ---------------------------------------------------------------------------
# PROVIDER_CAPABILITIES constant
# ---------------------------------------------------------------------------

class TestProviderCapabilities:
    def test_all_providers_present(self):
        for name in ALL_PROVIDERS:
            assert name in PROVIDER_CAPABILITIES, f"Missing: {name}"

    def test_expected_capability_keys(self):
        expected_keys = {"chat", "streaming", "image_generation", "vision", "tts", "embedding"}
        for name, caps in PROVIDER_CAPABILITIES.items():
            assert expected_keys == set(caps.keys()), f"Provider {name} has wrong keys"

    def test_all_providers_support_chat(self):
        for name, caps in PROVIDER_CAPABILITIES.items():
            assert caps["chat"] is True, f"{name} should support chat"

    def test_all_providers_support_streaming(self):
        for name, caps in PROVIDER_CAPABILITIES.items():
            assert caps["streaming"] is True, f"{name} should support streaming"

    def test_image_generation_providers(self):
        img_gen = {k for k, v in PROVIDER_CAPABILITIES.items() if v["image_generation"]}
        assert "openai" in img_gen
        assert "huggingface" in img_gen
        assert "anthropic" not in img_gen

    def test_vision_providers(self):
        vision = {k for k, v in PROVIDER_CAPABILITIES.items() if v["vision"]}
        assert "anthropic" in vision
        assert "openai" in vision
        assert "gemini" in vision
        assert "groq" not in vision  # Groq does not support vision per capabilities


# ---------------------------------------------------------------------------
# COMPLEXITY_TIERS constant
# ---------------------------------------------------------------------------

class TestComplexityTiers:
    def test_all_providers_have_tiers(self):
        for name in ALL_PROVIDERS:
            assert name in COMPLEXITY_TIERS, f"Missing tiers for: {name}"

    def test_all_tiers_present(self):
        for name, tiers in COMPLEXITY_TIERS.items():
            assert "simple" in tiers, f"{name} missing simple tier"
            assert "medium" in tiers, f"{name} missing medium tier"
            assert "complex" in tiers, f"{name} missing complex tier"

    def test_tier_values_are_strings(self):
        for name, tiers in COMPLEXITY_TIERS.items():
            for tier, model in tiers.items():
                assert isinstance(model, str) and model, \
                    f"{name}.{tier} should be a non-empty string"


# ---------------------------------------------------------------------------
# ProviderFactory.get_provider_capabilities
# ---------------------------------------------------------------------------

class TestGetProviderCapabilities:
    def test_specific_provider(self):
        caps = ProviderFactory.get_provider_capabilities("openai")
        assert isinstance(caps, dict)
        assert caps["chat"] is True
        assert caps["image_generation"] is True

    def test_all_providers_when_no_name(self):
        all_caps = ProviderFactory.get_provider_capabilities()
        assert "anthropic" in all_caps
        assert "openai" in all_caps

    def test_returns_copy_not_reference(self):
        """Mutating the returned dict should not affect the module-level constant."""
        caps = ProviderFactory.get_provider_capabilities("openai")
        caps["chat"] = False
        assert PROVIDER_CAPABILITIES["openai"]["chat"] is True

    def test_unknown_provider_returns_empty_dict(self):
        result = ProviderFactory.get_provider_capabilities("nonexistent")
        assert result == {}


# ---------------------------------------------------------------------------
# ProviderFactory.find_providers_with_capability
# ---------------------------------------------------------------------------

class TestFindProvidersWithCapability:
    def test_find_image_generation(self):
        providers = ProviderFactory.find_providers_with_capability("image_generation")
        assert "openai" in providers
        assert "huggingface" in providers
        assert "anthropic" not in providers

    def test_find_embedding(self):
        providers = ProviderFactory.find_providers_with_capability("embedding")
        assert "openai" in providers
        assert "groq" not in providers

    def test_unknown_capability_returns_empty(self):
        providers = ProviderFactory.find_providers_with_capability("teleportation")
        assert providers == []


# ---------------------------------------------------------------------------
# ProviderFactory.list_providers
# ---------------------------------------------------------------------------

class TestListProviders:
    @patch.dict("sys.modules", {
        "anthropic": _make_anthropic_mock(),
        "openai": _make_openai_mock(),
        "mistralai": MagicMock(),
        "cohere": MagicMock(),
        "google.generativeai": MagicMock(),
        "groq": MagicMock(),
        "huggingface_hub": MagicMock(),
        "requests": MagicMock(),
    })
    def test_returns_list(self):
        providers = ProviderFactory.list_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0

    @patch.dict("sys.modules", {
        "anthropic": _make_anthropic_mock(),
        "openai": _make_openai_mock(),
    })
    def test_ollama_always_listed(self):
        """Ollama has no third-party dep — it should always appear."""
        providers = ProviderFactory.list_providers()
        assert "ollama" in providers


# ---------------------------------------------------------------------------
# ProviderFactory.get_provider — singleton / caching
# ---------------------------------------------------------------------------

class TestGetProviderCaching:
    @patch("llm_providers.anthropic_provider.os.getenv", return_value="fake-anthropic-key")
    @patch.dict("sys.modules", {"anthropic": _make_anthropic_mock()})
    def test_same_instance_returned_twice(self, _mock_env):
        p1 = ProviderFactory.get_provider("anthropic")
        p2 = ProviderFactory.get_provider("anthropic")
        assert p1 is p2

    @patch("llm_providers.anthropic_provider.os.getenv", return_value="fake-anthropic-key")
    @patch("llm_providers.openai_provider.os.getenv", return_value="fake-openai-key")
    @patch.dict("sys.modules", {
        "anthropic": _make_anthropic_mock(),
        "openai": _make_openai_mock(),
    })
    def test_different_providers_are_different_instances(self, _env1, _env2):
        anthropic = ProviderFactory.get_provider("anthropic")
        openai = ProviderFactory.get_provider("openai")
        assert anthropic is not openai

    @patch("llm_providers.anthropic_provider.os.getenv", return_value="fake-anthropic-key")
    @patch.dict("sys.modules", {"anthropic": _make_anthropic_mock()})
    def test_clear_cache_forces_new_instance(self, _mock_env):
        p1 = ProviderFactory.get_provider("anthropic")
        ProviderFactory.clear_cache("anthropic")
        p2 = ProviderFactory.get_provider("anthropic")
        assert p1 is not p2

    @patch("llm_providers.anthropic_provider.os.getenv", return_value="fake-anthropic-key")
    @patch.dict("sys.modules", {"anthropic": _make_anthropic_mock()})
    def test_clear_all_cache(self, _mock_env):
        ProviderFactory.get_provider("anthropic")
        assert "anthropic" in ProviderFactory._instances
        ProviderFactory.clear_cache()
        assert ProviderFactory._instances == {}


# ---------------------------------------------------------------------------
# ProviderFactory.get_provider — error handling
# ---------------------------------------------------------------------------

class TestGetProviderErrors:
    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderFactory.get_provider("banana")

    def test_error_message_lists_available_providers(self):
        with pytest.raises(ValueError) as exc_info:
            ProviderFactory.get_provider("banana")
        assert "Available providers" in str(exc_info.value)

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            ProviderFactory.get_provider("")


# ---------------------------------------------------------------------------
# ProviderFactory.create_provider — fresh (non-cached) instances
# ---------------------------------------------------------------------------

class TestCreateProvider:
    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    @patch.dict("sys.modules", {"anthropic": _make_anthropic_mock()})
    def test_create_with_explicit_key(self, _mock_env):
        provider = ProviderFactory.create_provider("anthropic", api_key="sk-test-123")
        assert provider.api_key == "sk-test-123"

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    @patch.dict("sys.modules", {"anthropic": _make_anthropic_mock()})
    def test_create_does_not_cache(self, _mock_env):
        ProviderFactory.create_provider("anthropic", api_key="sk-1")
        assert "anthropic" not in ProviderFactory._instances

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    @patch.dict("sys.modules", {"anthropic": _make_anthropic_mock()})
    def test_create_two_independent_instances(self, _mock_env):
        p1 = ProviderFactory.create_provider("anthropic", api_key="sk-1")
        p2 = ProviderFactory.create_provider("anthropic", api_key="sk-2")
        assert p1 is not p2
        assert p1.api_key != p2.api_key

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    @patch.dict("sys.modules", {"anthropic": _make_anthropic_mock()})
    def test_create_with_model_override(self, _mock_env):
        provider = ProviderFactory.create_provider(
            "anthropic", api_key="sk-test", model="claude-3-5-haiku-20241022"
        )
        assert provider.model == "claude-3-5-haiku-20241022"

    def test_create_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderFactory.create_provider("banana", api_key="key")


# ---------------------------------------------------------------------------
# ProviderFactory.select_model_by_complexity
# ---------------------------------------------------------------------------

class TestSelectModelByComplexity:
    def test_simple_query_returns_simple_model(self):
        model, meta = ProviderFactory.select_model_by_complexity(
            "What is Python?", provider="openai"
        )
        assert model == COMPLEXITY_TIERS["openai"]["simple"]
        assert meta["complexity"] == "simple"

    def test_complex_query_returns_complex_model(self):
        long_query = "Design and implement a comprehensive microservices architecture " * 3
        model, meta = ProviderFactory.select_model_by_complexity(
            long_query, provider="anthropic"
        )
        assert meta["complexity"] == "complex"

    def test_cheap_budget_downgrades_medium_to_simple(self):
        # A medium-length query that would normally be medium complexity
        query = "Explain how neural networks work in detail"
        model_balanced, _ = ProviderFactory.select_model_by_complexity(
            query, provider="openai", budget_tier="balanced"
        )
        model_cheap, meta_cheap = ProviderFactory.select_model_by_complexity(
            query, provider="openai", budget_tier="cheap"
        )
        # Cheap should pick simple or medium (never higher than balanced)
        assert meta_cheap["budget_tier"] == "cheap"

    def test_premium_budget_upgrades_simple_to_medium(self):
        model, meta = ProviderFactory.select_model_by_complexity(
            "What is 2+2?", provider="anthropic", budget_tier="premium"
        )
        # A very short, simple query upgraded to medium by premium budget
        assert meta["budget_tier"] == "premium"

    def test_metadata_contains_expected_keys(self):
        _, meta = ProviderFactory.select_model_by_complexity(
            "Hello", provider="groq"
        )
        assert "complexity" in meta
        assert "cost_tier" in meta
        assert "budget_tier" in meta

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="No complexity tiers"):
            ProviderFactory.select_model_by_complexity("Query", provider="banana")
