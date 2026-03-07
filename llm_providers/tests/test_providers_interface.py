"""
Tests that each provider correctly implements the BaseLLMProvider interface
and that complete() / stream_complete() / list_models() work as expected,
with all external SDK calls mocked.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from llm_providers import (
    BaseLLMProvider, Message, CompletionResponse,
)


# ---------------------------------------------------------------------------
# BaseLLMProvider — abstract method enforcement
# ---------------------------------------------------------------------------

class TestBaseLLMProviderAbstract:
    def test_cannot_instantiate_base_directly(self):
        with pytest.raises(TypeError):
            BaseLLMProvider(api_key="key")  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_all_abstract_methods(self):
        """A minimal subclass missing one abstract method cannot be instantiated."""
        class Incomplete(BaseLLMProvider):
            def complete(self, messages, **kwargs):
                return CompletionResponse(content="", model="m", usage={})
            # stream_complete and list_models intentionally omitted

        with pytest.raises(TypeError):
            Incomplete(api_key="key")

    def test_generate_image_raises_not_implemented_by_default(self):
        class Minimal(BaseLLMProvider):
            def complete(self, messages, **kwargs):
                return CompletionResponse(content="", model="m", usage={})
            def stream_complete(self, messages, **kwargs):
                return iter([])
            def list_models(self):
                return []

        p = Minimal(api_key="key")
        with pytest.raises(NotImplementedError):
            p.generate_image("a cat")

    def test_analyze_image_raises_not_implemented_by_default(self):
        class Minimal(BaseLLMProvider):
            def complete(self, messages, **kwargs):
                return CompletionResponse(content="", model="m", usage={})
            def stream_complete(self, messages, **kwargs):
                return iter([])
            def list_models(self):
                return []

        p = Minimal(api_key="key")
        with pytest.raises(NotImplementedError):
            p.analyze_image("base64data")


# ---------------------------------------------------------------------------
# AnthropicProvider
# ---------------------------------------------------------------------------

class TestAnthropicProvider:
    @pytest.fixture
    def mock_anthropic_sdk(self):
        mock_sdk = MagicMock()
        mock_client = MagicMock()
        mock_sdk.Anthropic.return_value = mock_client
        return mock_sdk, mock_client

    @patch("llm_providers.anthropic_provider.os.getenv", return_value="sk-ant-test")
    def test_instantiation_uses_env_key(self, _mock_env, mock_anthropic_sdk):
        sdk, _ = mock_anthropic_sdk
        with patch.dict("sys.modules", {"anthropic": sdk}):
            from llm_providers.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider()
            assert provider.api_key == "sk-ant-test"

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    def test_instantiation_without_key_raises(self, _mock_env, mock_anthropic_sdk):
        sdk, _ = mock_anthropic_sdk
        with patch.dict("sys.modules", {"anthropic": sdk}):
            from llm_providers.anthropic_provider import AnthropicProvider
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                AnthropicProvider()

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    def test_explicit_key_bypasses_env(self, _mock_env, mock_anthropic_sdk):
        sdk, _ = mock_anthropic_sdk
        with patch.dict("sys.modules", {"anthropic": sdk}):
            from llm_providers.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider(api_key="sk-explicit")
            assert provider.api_key == "sk-explicit"

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    def test_default_model_set(self, _mock_env, mock_anthropic_sdk):
        sdk, _ = mock_anthropic_sdk
        with patch.dict("sys.modules", {"anthropic": sdk}):
            from llm_providers.anthropic_provider import AnthropicProvider
            p = AnthropicProvider(api_key="sk-test")
            assert p.model == AnthropicProvider.DEFAULT_MODEL

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    def test_complete_returns_completion_response(self, _mock_env, mock_anthropic_sdk, anthropic_api_response):
        sdk, client = mock_anthropic_sdk
        client.messages.create.return_value = anthropic_api_response
        with patch.dict("sys.modules", {"anthropic": sdk}):
            from llm_providers.anthropic_provider import AnthropicProvider
            p = AnthropicProvider(api_key="sk-test")
            result = p.complete([Message(role="user", content="Hi")])
            assert isinstance(result, CompletionResponse)
            assert result.content == "Hello from Claude!"
            assert result.model == "claude-sonnet-4-5-20250929"
            assert result.usage["total_tokens"] == 15

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    def test_complete_passes_kwargs_to_sdk(self, _mock_env, mock_anthropic_sdk, anthropic_api_response):
        sdk, client = mock_anthropic_sdk
        client.messages.create.return_value = anthropic_api_response
        with patch.dict("sys.modules", {"anthropic": sdk}):
            from llm_providers.anthropic_provider import AnthropicProvider
            p = AnthropicProvider(api_key="sk-test")
            p.complete([Message(role="user", content="Hi")], max_tokens=512)
            call_kwargs = client.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 512

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    def test_list_models_returns_list_of_strings(self, _mock_env, mock_anthropic_sdk):
        sdk, _ = mock_anthropic_sdk
        with patch.dict("sys.modules", {"anthropic": sdk}):
            from llm_providers.anthropic_provider import AnthropicProvider
            p = AnthropicProvider(api_key="sk-test")
            models = p.list_models()
            assert isinstance(models, list)
            assert all(isinstance(m, str) for m in models)
            assert len(models) > 0

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    def test_stream_complete_is_generator(self, _mock_env, mock_anthropic_sdk):
        sdk, client = mock_anthropic_sdk
        stream_ctx = MagicMock()
        stream_ctx.__enter__ = MagicMock(return_value=stream_ctx)
        stream_ctx.__exit__ = MagicMock(return_value=False)
        stream_ctx.text_stream = iter(["Hello", " world"])
        client.messages.stream.return_value = stream_ctx
        with patch.dict("sys.modules", {"anthropic": sdk}):
            from llm_providers.anthropic_provider import AnthropicProvider
            p = AnthropicProvider(api_key="sk-test")
            chunks = list(p.stream_complete([Message(role="user", content="Hi")]))
            assert chunks == ["Hello", " world"]

    @patch("llm_providers.anthropic_provider.os.getenv", return_value=None)
    def test_has_chat_method(self, _mock_env, mock_anthropic_sdk):
        sdk, _ = mock_anthropic_sdk
        with patch.dict("sys.modules", {"anthropic": sdk}):
            from llm_providers.anthropic_provider import AnthropicProvider
            p = AnthropicProvider(api_key="sk-test")
            assert callable(p.chat)


# ---------------------------------------------------------------------------
# OpenAIProvider
# ---------------------------------------------------------------------------

class TestOpenAIProvider:
    @pytest.fixture
    def mock_openai_sdk(self):
        mock_sdk = MagicMock()
        mock_client = MagicMock()
        mock_sdk.OpenAI.return_value = mock_client
        return mock_sdk, mock_client

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_raises_without_key(self, _mock_env, mock_openai_sdk):
        sdk, _ = mock_openai_sdk
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIProvider()

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_explicit_key(self, _mock_env, mock_openai_sdk):
        sdk, _ = mock_openai_sdk
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key="sk-openai-test")
            assert p.api_key == "sk-openai-test"

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_complete_returns_completion_response(self, _mock_env, mock_openai_sdk, openai_chat_response):
        sdk, client = mock_openai_sdk
        client.chat.completions.create.return_value = openai_chat_response
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key="sk-test")
            result = p.complete([Message(role="user", content="Hello")])
            assert isinstance(result, CompletionResponse)
            assert result.content == "Hello from GPT!"
            assert result.usage["total_tokens"] == 15

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_stream_complete_yields_strings(self, _mock_env, mock_openai_sdk):
        sdk, client = mock_openai_sdk
        chunk1 = MagicMock(); chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
        chunk2 = MagicMock(); chunk2.choices = [MagicMock(delta=MagicMock(content=" world"))]
        chunk3 = MagicMock(); chunk3.choices = [MagicMock(delta=MagicMock(content=None))]
        client.chat.completions.create.return_value = iter([chunk1, chunk2, chunk3])
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key="sk-test")
            chunks = list(p.stream_complete([Message(role="user", content="Hi")]))
            assert chunks == ["Hello", " world"]

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_generate_image_returns_image_response(self, _mock_env, mock_openai_sdk, openai_image_response):
        from llm_providers import ImageResponse
        sdk, client = mock_openai_sdk
        client.images.generate.return_value = openai_image_response
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key="sk-test")
            result = p.generate_image("A sunset over the mountains")
            assert isinstance(result, ImageResponse)
            assert result.image_data == "aGVsbG8="
            assert result.model == "dall-e-3"

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_generate_speech_validates_empty_text(self, _mock_env, mock_openai_sdk):
        sdk, _ = mock_openai_sdk
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key="sk-test")
            with pytest.raises(ValueError, match="empty"):
                p.generate_speech("")

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_generate_speech_validates_text_too_long(self, _mock_env, mock_openai_sdk):
        sdk, _ = mock_openai_sdk
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key="sk-test")
            with pytest.raises(ValueError, match="too long"):
                p.generate_speech("x" * 4097)

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_generate_speech_validates_invalid_voice(self, _mock_env, mock_openai_sdk):
        sdk, _ = mock_openai_sdk
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key="sk-test")
            with pytest.raises(ValueError, match="Invalid voice"):
                p.generate_speech("Hello", voice="darth_vader")

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_generate_speech_validates_speed(self, _mock_env, mock_openai_sdk):
        sdk, _ = mock_openai_sdk
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key="sk-test")
            with pytest.raises(ValueError, match="Speed"):
                p.generate_speech("Hello", speed=10.0)

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_transcribe_audio_file_not_found(self, _mock_env, mock_openai_sdk):
        sdk, _ = mock_openai_sdk
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key="sk-test")
            with pytest.raises(FileNotFoundError):
                p.transcribe_audio("/no/such/file.mp3")

    @patch("llm_providers.openai_provider.os.getenv", return_value=None)
    def test_transcribe_audio_invalid_format(self, _mock_env, mock_openai_sdk, tmp_path):
        sdk, _ = mock_openai_sdk
        bad_file = tmp_path / "audio.txt"
        bad_file.write_text("not audio")
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key="sk-test")
            with pytest.raises(ValueError, match="Invalid audio format"):
                p.transcribe_audio(str(bad_file))


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------

class TestOllamaProvider:
    @pytest.fixture
    def mock_ollama_unavailable(self):
        """Patch requests so Ollama appears offline."""
        with patch("llm_providers.ollama_provider.requests") as mock_req:
            mock_req.get.side_effect = ConnectionError("Server not running")
            yield mock_req

    @pytest.fixture
    def mock_ollama_available(self):
        """Patch requests so Ollama appears online with two models."""
        with patch("llm_providers.ollama_provider.requests") as mock_req:
            tags_response = MagicMock()
            tags_response.status_code = 200
            tags_response.json.return_value = {
                "models": [
                    {"name": "llama3.2", "size": 1_000_000, "digest": "abc", "modified_at": "2024-01-01"},
                    {"name": "llava", "size": 2_000_000, "digest": "def", "modified_at": "2024-01-01"},
                ]
            }
            show_response = MagicMock()
            show_response.status_code = 200
            show_response.json.return_value = {"details": {"parameter_size": "7B", "families": []}}

            mock_req.get.return_value = tags_response
            mock_req.post.return_value = show_response
            yield mock_req

    def test_instantiates_without_api_key(self, mock_ollama_unavailable):
        from llm_providers.ollama_provider import OllamaProvider
        p = OllamaProvider()
        assert p.api_key == "local"

    def test_unavailable_when_server_down(self, mock_ollama_unavailable):
        from llm_providers.ollama_provider import OllamaProvider
        p = OllamaProvider()
        assert p.available is False

    def test_available_when_server_running(self, mock_ollama_available):
        from llm_providers.ollama_provider import OllamaProvider
        p = OllamaProvider()
        assert p.available is True

    def test_list_models_when_unavailable(self, mock_ollama_unavailable):
        from llm_providers.ollama_provider import OllamaProvider
        p = OllamaProvider()
        models = p.list_models()
        assert models == []

    def test_list_models_when_available(self, mock_ollama_available):
        from llm_providers.ollama_provider import OllamaProvider
        p = OllamaProvider()
        models = p.list_models()
        assert "llama3.2" in models
        assert "llava" in models

    def test_complete_raises_when_unavailable(self, mock_ollama_unavailable):
        from llm_providers.ollama_provider import OllamaProvider
        p = OllamaProvider()
        with pytest.raises(RuntimeError, match="not available"):
            p.complete([Message(role="user", content="Hi")])

    def test_complete_returns_completion_response(self, mock_ollama_available):
        from llm_providers.ollama_provider import OllamaProvider
        p = OllamaProvider(model="llama3.2")

        chat_response = MagicMock()
        chat_response.status_code = 200
        chat_response.json.return_value = {
            "message": {"content": "Hello from Ollama!"},
            "model": "llama3.2",
            "prompt_eval_count": 5,
            "eval_count": 10,
            "created_at": "2024-01-01",
            "done": True,
        }
        mock_ollama_available.post.return_value = chat_response

        result = p.complete([Message(role="user", content="Hello")])
        assert isinstance(result, CompletionResponse)
        assert result.content == "Hello from Ollama!"

    def test_get_status_structure(self, mock_ollama_unavailable):
        from llm_providers.ollama_provider import OllamaProvider
        p = OllamaProvider()
        status = p.get_status()
        assert "name" in status
        assert "available" in status
        assert "host" in status
        assert status["name"] == "ollama"

    def test_stream_complete_raises_when_unavailable(self, mock_ollama_unavailable):
        from llm_providers.ollama_provider import OllamaProvider
        p = OllamaProvider()
        with pytest.raises(RuntimeError, match="not available"):
            list(p.stream_complete([Message(role="user", content="Hi")]))


# ---------------------------------------------------------------------------
# MistralProvider
# ---------------------------------------------------------------------------

class TestMistralProvider:
    @patch("llm_providers.mistral_provider.os.getenv", return_value=None)
    def test_raises_without_key(self, _mock_env):
        with patch.dict("sys.modules", {"requests": MagicMock()}):
            from llm_providers.mistral_provider import MistralProvider
            with pytest.raises(ValueError, match="MISTRAL_API_KEY"):
                MistralProvider()

    @patch("llm_providers.mistral_provider.os.getenv", return_value=None)
    def test_complete_returns_completion_response(self, _mock_env):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Bonjour!"}, "finish_reason": "stop"}],
            "model": "mistral-large-2411",
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            "id": "cmpl-abc",
        }
        mock_requests.post.return_value = mock_response
        with patch.dict("sys.modules", {"requests": mock_requests}):
            from llm_providers.mistral_provider import MistralProvider
            # patch the internal self.requests used by the provider
            p = MistralProvider(api_key="sk-mistral-test")
            p.requests = mock_requests
            result = p.complete([Message(role="user", content="Bonjour")])
            assert isinstance(result, CompletionResponse)
            assert result.content == "Bonjour!"

    @patch("llm_providers.mistral_provider.os.getenv", return_value=None)
    def test_list_models_fallback(self, _mock_env):
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("network error")
        with patch.dict("sys.modules", {"requests": mock_requests}):
            from llm_providers.mistral_provider import MistralProvider
            p = MistralProvider(api_key="sk-test")
            p.requests = mock_requests
            models = p.list_models()
            assert isinstance(models, list)
            assert len(models) > 0


# ---------------------------------------------------------------------------
# GroqProvider
# ---------------------------------------------------------------------------

class TestGroqProvider:
    @pytest.fixture
    def mock_openai_sdk(self):
        mock_sdk = MagicMock()
        mock_client = MagicMock()
        mock_sdk.OpenAI.return_value = mock_client
        return mock_sdk, mock_client

    @patch("llm_providers.groq_provider.os.getenv", return_value=None)
    def test_raises_without_key(self, _mock_env, mock_openai_sdk):
        sdk, _ = mock_openai_sdk
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.groq_provider import GroqProvider
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                GroqProvider()

    @patch("llm_providers.groq_provider.os.getenv", return_value=None)
    def test_complete_returns_completion_response(self, _mock_env, mock_openai_sdk, openai_chat_response):
        sdk, client = mock_openai_sdk
        client.chat.completions.create.return_value = openai_chat_response
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.groq_provider import GroqProvider
            p = GroqProvider(api_key="sk-groq-test")
            result = p.complete([Message(role="user", content="Fast!")])
            assert isinstance(result, CompletionResponse)

    @patch("llm_providers.groq_provider.os.getenv", return_value=None)
    def test_list_models_fallback(self, _mock_env, mock_openai_sdk):
        sdk, client = mock_openai_sdk
        client.models.list.side_effect = Exception("network error")
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.groq_provider import GroqProvider
            p = GroqProvider(api_key="sk-groq-test")
            models = p.list_models()
            assert isinstance(models, list)
            assert "llama-3.3-70b-versatile" in models

    @patch("llm_providers.groq_provider.os.getenv", return_value=None)
    def test_uses_groq_base_url(self, _mock_env, mock_openai_sdk):
        sdk, _ = mock_openai_sdk
        with patch.dict("sys.modules", {"openai": sdk}):
            from llm_providers.groq_provider import GroqProvider
            GroqProvider(api_key="sk-groq-test")
            call_kwargs = sdk.OpenAI.call_args[1]
            assert "groq.com" in call_kwargs.get("base_url", "")


# ---------------------------------------------------------------------------
# Provider interface compliance — parametrized
# ---------------------------------------------------------------------------

PROVIDER_INTERFACE_CASES = [
    ("anthropic", "llm_providers.anthropic_provider.AnthropicProvider", "ANTHROPIC_API_KEY"),
    ("openai",    "llm_providers.openai_provider.OpenAIProvider",       "OPENAI_API_KEY"),
    ("mistral",   "llm_providers.mistral_provider.MistralProvider",     "MISTRAL_API_KEY"),
    ("cohere",    "llm_providers.cohere_provider.CohereProvider",       "COHERE_API_KEY"),
    ("gemini",    "llm_providers.gemini_provider.GeminiProvider",       "GEMINI_API_KEY"),
    ("perplexity","llm_providers.perplexity_provider.PerplexityProvider","PERPLEXITY_API_KEY"),
    ("groq",      "llm_providers.groq_provider.GroqProvider",           "GROQ_API_KEY"),
    ("huggingface","llm_providers.huggingface_provider.HuggingFaceProvider","HUGGINGFACE_API_KEY"),
]


@pytest.mark.parametrize("provider_name,class_path,env_var", PROVIDER_INTERFACE_CASES)
def test_provider_requires_api_key(provider_name, class_path, env_var):
    """Every keyed provider raises ValueError when no key is available."""
    module_path, class_name = class_path.rsplit(".", 1)
    import importlib

    # Build a mock that satisfies every possible third-party import
    generic_mock = MagicMock()
    generic_mock.Anthropic.return_value = MagicMock()
    generic_mock.OpenAI.return_value = MagicMock()
    generic_mock.Client.return_value = MagicMock()
    generic_mock.configure = MagicMock()
    generic_mock.InferenceClient.return_value = MagicMock()

    sdk_names = ["anthropic", "openai", "cohere", "google.generativeai",
                 "mistralai", "groq", "huggingface_hub", "requests"]
    mock_modules = {name: generic_mock for name in sdk_names}

    with patch.dict("sys.modules", mock_modules):
        with patch(f"{module_path}.os.getenv", return_value=None):
            # Force reimport so our mocks take effect
            if module_path in __import__("sys").modules:
                del __import__("sys").modules[module_path]
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            with pytest.raises(ValueError, match=env_var.split("_")[0]):
                cls()
