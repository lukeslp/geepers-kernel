from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

SHARED_DIR = Path(__file__).resolve().parents[1]
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

import shared.config as shared_config  # noqa: E402

sys.modules.setdefault("config", shared_config)

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

from shared.tools import ToolModuleBase  # noqa: E402
from shared.tools.registry import ToolRegistry, reset_registry


@pytest.fixture(autouse=True)
def _reset_registry():
    reset_registry()
    yield
    reset_registry()


def test_register_tool_validates_schema():
    registry = ToolRegistry()

    invalid_schema = {
        "type": "function",
        "function": {
            "name": "invalid_tool",
            # Missing description field
            "parameters": {"type": "object", "properties": {}},
        },
    }

    with pytest.raises(ValueError):
        registry.register_tool(
            name="invalid_tool",
            schema=invalid_schema,
            handler=lambda: None,
        )

    metrics = registry.get_metrics()
    assert metrics["registered_tools"] == 0
    assert metrics["validation_failures"], "Validation failure should be recorded"


def test_discover_tool_modules_auto_registers_tools():
    module_name = "shared.tools._dummy_auto_discover"
    module = types.ModuleType(module_name)

    class DummyTool(ToolModuleBase):
        name = "dummy_module"
        display_name = "Dummy Module"
        description = "Dummy tool for testing"

        def initialize(self):
            self.tool_schemas = [
                {
                    "type": "function",
                    "function": {
                        "name": "dummy_action",
                        "description": "Perform dummy action",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "A value"}
                            },
                            "required": [],
                        },
                    },
                }
            ]

        def dummy_action(self, value: str = "ok"):
            return {"value": value}

    setattr(module, "DummyTool", DummyTool)
    sys.modules[module_name] = module

    registry = ToolRegistry()
    discovery = registry.discover_tool_modules(
        module_names=[module_name],
        auto_register=True,
        skip_errors=False,
    )

    try:
        assert module_name in discovery["modules"]
        handler = registry.get_tool_handler("dummy_action")
        assert handler is not None
        assert handler(value="test") == {"value": "test"}

        metrics = registry.get_metrics()
        assert metrics["registered_tools"] >= 1
    finally:
        sys.modules.pop(module_name, None)

