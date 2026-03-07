"""
Shared fixtures for llm-providers tests.

All fixtures are designed to avoid real API calls. Provider SDK packages
(anthropic, openai, etc.) are mocked at the import level so tests run
even when optional deps are not installed.
"""

import pytest
from unittest.mock import MagicMock, patch
from llm_providers import Message, CompletionResponse, ImageResponse


# ---------------------------------------------------------------------------
# Common message fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_message():
    return Message(role="user", content="Hello, world!")


@pytest.fixture
def system_message():
    return Message(role="system", content="You are a helpful assistant.")


@pytest.fixture
def assistant_message():
    return Message(role="assistant", content="Hi there!")


@pytest.fixture
def simple_messages(system_message, user_message):
    return [system_message, user_message]


# ---------------------------------------------------------------------------
# Canned API responses that match each provider's SDK shape
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_completion_response():
    """A CompletionResponse the test code can assert against."""
    return CompletionResponse(
        content="Hello from the mock!",
        model="test-model",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        metadata={"id": "msg_abc123", "stop_reason": "end_turn"},
    )


@pytest.fixture
def anthropic_api_response():
    """Mimics the object returned by anthropic.Anthropic().messages.create()."""
    response = MagicMock()
    response.content = [MagicMock(text="Hello from Claude!")]
    response.model = "claude-sonnet-4-5-20250929"
    response.id = "msg_abc123"
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=10, output_tokens=5)
    return response


@pytest.fixture
def openai_chat_response():
    """Mimics the object returned by openai.OpenAI().chat.completions.create()."""
    response = MagicMock()
    response.choices = [MagicMock(
        message=MagicMock(content="Hello from GPT!"),
        finish_reason="stop",
    )]
    response.model = "gpt-4o"
    response.id = "chatcmpl-abc123"
    response.usage = MagicMock(
        prompt_tokens=10, completion_tokens=5, total_tokens=15
    )
    return response


@pytest.fixture
def openai_image_response():
    """Mimics the object returned by openai.OpenAI().images.generate()."""
    response = MagicMock()
    image_data = MagicMock()
    image_data.b64_json = "aGVsbG8="  # base64 of "hello"
    image_data.revised_prompt = "A revised prompt"
    response.data = [image_data]
    return response


# ---------------------------------------------------------------------------
# Factory cache reset — runs after each test to prevent singleton pollution
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_provider_cache():
    """Clear ProviderFactory._instances between tests."""
    from llm_providers import ProviderFactory
    ProviderFactory.clear_cache()
    yield
    ProviderFactory.clear_cache()
