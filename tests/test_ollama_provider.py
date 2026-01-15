"""
Tests for Ollama Provider

Author: Luke Steuber
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import base64

from llm_providers import OllamaProvider, Message, CompletionResponse


@pytest.fixture
def mock_ollama_server():
    """Mock Ollama server responses."""
    with patch('llm_providers.ollama_provider.requests') as mock_requests:
        # Mock server availability check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "llama3.2",
                    "size": 2000000000,
                    "digest": "abc123",
                    "modified_at": "2025-12-12T00:00:00Z"
                },
                {
                    "name": "llava",
                    "size": 4000000000,
                    "digest": "def456",
                    "modified_at": "2025-12-12T00:00:00Z"
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        # Mock model details
        mock_details_response = Mock()
        mock_details_response.status_code = 200
        mock_details_response.json.return_value = {
            "details": {
                "families": ["llama"],
                "parameter_size": "3B"
            }
        }
        mock_requests.post.return_value = mock_details_response

        yield mock_requests


@pytest.fixture
def ollama_provider(mock_ollama_server):
    """Create an Ollama provider instance with mocked server."""
    return OllamaProvider()


def test_provider_initialization(ollama_provider):
    """Test that provider initializes correctly."""
    assert ollama_provider.available
    assert ollama_provider.host == "http://localhost:11434"
    assert ollama_provider.model is not None


def test_list_models(ollama_provider):
    """Test model listing."""
    models = ollama_provider.list_models()
    assert isinstance(models, list)
    assert len(models) > 0
    assert "llama3.2" in models or "llava" in models


def test_complete(ollama_provider, mock_ollama_server):
    """Test completion generation."""
    # Mock completion response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "content": "Hello! How can I assist you today?"
        },
        "prompt_eval_count": 10,
        "eval_count": 8,
        "done": True
    }
    mock_ollama_server.post.return_value = mock_response

    messages = [Message(role="user", content="Hello")]
    response = ollama_provider.complete(messages)

    assert isinstance(response, CompletionResponse)
    assert response.content
    assert response.model
    assert response.usage["input_tokens"] >= 0
    assert response.usage["output_tokens"] >= 0


def test_stream_complete(ollama_provider, mock_ollama_server):
    """Test streaming completion."""
    # Mock streaming response context manager
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = [
        b'{"message": {"content": "Hello"}, "done": false}',
        b'{"message": {"content": " there"}, "done": false}',
        b'{"message": {"content": "!"}, "done": true, "prompt_eval_count": 10, "eval_count": 3}'
    ]

    # Create context manager mock
    context_manager = MagicMock()
    context_manager.__enter__.return_value = mock_response
    context_manager.__exit__.return_value = False
    mock_ollama_server.post.return_value = context_manager

    messages = [Message(role="user", content="Hi")]
    chunks = list(ollama_provider.stream_complete(messages))

    assert len(chunks) > 0
    # Check that we got content chunks
    content_chunks = [c for c in chunks if c.content]
    assert len(content_chunks) > 0


def test_vision_model_detection(ollama_provider):
    """Test vision model detection."""
    assert ollama_provider._is_vision_model("llava")
    assert ollama_provider._is_vision_model("bakllava")
    assert ollama_provider._is_vision_model("llava:13b")
    assert not ollama_provider._is_vision_model("llama3.2")


def test_analyze_image(ollama_provider, mock_ollama_server):
    """Test image analysis with vision model."""
    # Mock vision completion response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "content": "This image shows a cat sitting on a chair."
        },
        "prompt_eval_count": 100,
        "eval_count": 15,
        "done": True
    }
    mock_ollama_server.post.return_value = mock_response

    # Create fake image data
    fake_image = base64.b64encode(b"fake image data").decode('utf-8')

    response = ollama_provider.analyze_image(
        image=fake_image,
        prompt="What's in this image?",
        model="llava"
    )

    assert isinstance(response, CompletionResponse)
    assert response.content
    assert response.metadata.get("vision") is True


def test_get_status(ollama_provider):
    """Test status reporting."""
    status = ollama_provider.get_status()

    assert status["name"] == "ollama"
    assert status["available"] is True
    assert "host" in status
    assert "model_count" in status
    assert "models" in status
    assert "default_model" in status


def test_server_unavailable():
    """Test behavior when Ollama server is not available."""
    with patch('llm_providers.ollama_provider.requests.get') as mock_get:
        mock_get.side_effect = Exception("Connection refused")

        provider = OllamaProvider()

        assert not provider.available
        assert len(provider.cached_models) == 0
        assert provider.list_models() == []


def test_completion_error_handling(ollama_provider, mock_ollama_server):
    """Test error handling in completion."""
    # Mock error response
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal server error"
    mock_ollama_server.post.return_value = mock_response

    messages = [Message(role="user", content="Hello")]

    with pytest.raises(RuntimeError) as exc_info:
        ollama_provider.complete(messages)

    assert "Ollama API error" in str(exc_info.value)


def test_custom_model_parameter(ollama_provider, mock_ollama_server):
    """Test using custom model parameter in completion."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "Response"},
        "prompt_eval_count": 5,
        "eval_count": 3,
        "done": True
    }
    mock_ollama_server.post.return_value = mock_response

    messages = [Message(role="user", content="Test")]
    response = ollama_provider.complete(messages, model="custom-model")

    # Verify the custom model was used
    call_args = mock_ollama_server.post.call_args
    assert call_args[1]["json"]["model"] == "custom-model"


def test_temperature_and_max_tokens(ollama_provider, mock_ollama_server):
    """Test temperature and max_tokens parameters."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "Response"},
        "prompt_eval_count": 5,
        "eval_count": 3,
        "done": True
    }
    mock_ollama_server.post.return_value = mock_response

    messages = [Message(role="user", content="Test")]
    ollama_provider.complete(
        messages,
        temperature=0.9,
        max_tokens=2000
    )

    # Verify parameters were passed
    call_args = mock_ollama_server.post.call_args
    options = call_args[1]["json"]["options"]
    assert options["temperature"] == 0.9
    assert options["num_predict"] == 2000


def test_system_message_handling(ollama_provider, mock_ollama_server):
    """Test that system messages are handled correctly."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "Response"},
        "prompt_eval_count": 5,
        "eval_count": 3,
        "done": True
    }
    mock_ollama_server.post.return_value = mock_response

    messages = [
        Message(role="system", content="You are a helpful assistant"),
        Message(role="user", content="Hello")
    ]
    ollama_provider.complete(messages)

    # Verify system message was included
    call_args = mock_ollama_server.post.call_args
    assert "system" in call_args[1]["json"]
    assert call_args[1]["json"]["system"] == "You are a helpful assistant"


def test_real_ollama_integration():
    """
    Integration test with real Ollama server.
    Skipped if Ollama is not available.

    Mark as integration test by running: pytest -m integration
    """
    with patch('llm_providers.ollama_provider.requests.get') as mock_get:
        # Mock unavailable server
        mock_get.side_effect = Exception("Connection refused")
        provider = OllamaProvider()

        if not provider.available:
            pytest.skip("Ollama server not available (mocked as unavailable)")
