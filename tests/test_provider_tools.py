import importlib
import sys
import types
from pathlib import Path

import pytest

SHARED_DIR = Path(__file__).resolve().parents[1]
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

pandas_stub = types.ModuleType("pandas")
pandas_stub.DataFrame = object
pandas_stub.Series = object


def _not_impl(*_args, **_kwargs):
    raise NotImplementedError("pandas stub invoked")


pandas_stub.to_numeric = _not_impl
pandas_stub.read_csv = _not_impl
sys.modules.setdefault("pandas", pandas_stub)

arxiv_stub = types.ModuleType("arxiv")


class _StubClient:
    def __init__(self, *args, **kwargs):
        pass

    def results(self, *_args, **_kwargs):
        return []


class _StubSearch:
    def __init__(self, *args, **kwargs):
        pass


class _StubSortCriterion:
    Relevance = "relevance"
    LastUpdatedDate = "last_updated"


arxiv_stub.Client = _StubClient
arxiv_stub.Search = _StubSearch
arxiv_stub.SortCriterion = _StubSortCriterion
sys.modules.setdefault("arxiv", arxiv_stub)

from llm_providers import CompletionResponse, ImageResponse
from shared.tools import provider_registry
from shared.tools.registry import reset_registry


def _install_stub_provider(module_name: str):
    """Install a stub provider module into sys.modules."""

    module = types.ModuleType(module_name)

    class DummyProvider:
        DEFAULT_MODEL = "dummy-model"

        def __init__(self, api_key=None, model=None):
            if not api_key:
                raise ValueError("api key required")
            self.api_key = api_key
            self.model = model or self.DEFAULT_MODEL

        def complete(self, messages, **kwargs):
            return CompletionResponse(
                content="hello world",
                model=self.model,
                usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                metadata={"finish_reason": "stop"},
            )

        def stream_complete(self, messages, **kwargs):
            yield "chunk"

        def analyze_image(self, image, prompt="describe", **kwargs):
            return CompletionResponse(
                content="image description",
                model=self.model,
                usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                metadata={"finish_reason": "stop"},
            )

        def generate_image(self, prompt, **kwargs):
            return ImageResponse(image_data="aGVsbG8=", model=self.model)

        def list_models(self):
            return [self.DEFAULT_MODEL]

    module.OpenAIProvider = DummyProvider
    sys.modules[module_name] = module


@pytest.fixture(autouse=True)
def reset_tool_registry():
    """Reset registry before each test."""
    reset_registry()
    yield
    reset_registry()


def test_register_provider_tools_success(monkeypatch):
    module_path = "llm_providers.openai_provider"
    _install_stub_provider(module_path)

    import shared.tools.openai_tools as openai_tools

    importlib.reload(openai_tools)
    importlib.reload(provider_registry)

    monkeypatch.setattr(
        provider_registry,
        "PROVIDER_TOOL_CLASSES",
        [("shared.tools.openai_tools", "OpenAITools")],
    )

    result = provider_registry.register_provider_tools(
        config={"openai": {"api_key": "test-key"}}
    )

    assert result["registered"] == ["openai"]
    assert result["errors"] == {}

    registry = provider_registry.get_registry()
    handler = registry.get_tool_handler("openai_chat")
    output = handler(messages=[{"role": "user", "content": "Hi"}])

    assert output["content"] == "hello world"
    assert output["model"] == "dummy-model"
    assert output["finish_reason"] == "stop"


def test_register_provider_tools_missing_key(monkeypatch):
    module_path = "llm_providers.openai_provider"
    _install_stub_provider(module_path)

    import shared.tools.openai_tools as openai_tools

    importlib.reload(openai_tools)
    importlib.reload(provider_registry)

    monkeypatch.setattr(
        provider_registry,
        "PROVIDER_TOOL_CLASSES",
        [("shared.tools.openai_tools", "OpenAITools")],
    )

    result = provider_registry.register_provider_tools(config={})

    assert result["registered"] == []
    assert "openai" in result["errors"]


