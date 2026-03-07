"""
Tests for the public dataclasses: Message, CompletionResponse,
ImageResponse, AudioResponse, VisionMessage.
"""

import pytest
from llm_providers import Message, CompletionResponse, ImageResponse
from llm_providers import AudioResponse, VisionMessage


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class TestMessage:
    def test_basic_creation(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.metadata is None

    def test_with_metadata(self):
        meta = {"source": "test"}
        msg = Message(role="assistant", content="Hi", metadata=meta)
        assert msg.metadata == {"source": "test"}

    def test_system_role(self):
        msg = Message(role="system", content="You are helpful.")
        assert msg.role == "system"

    def test_equality(self):
        a = Message(role="user", content="Hi")
        b = Message(role="user", content="Hi")
        assert a == b

    def test_inequality(self):
        a = Message(role="user", content="Hi")
        b = Message(role="user", content="Bye")
        assert a != b

    def test_content_required(self):
        # content is a required positional arg — omitting it raises TypeError
        with pytest.raises(TypeError):
            Message(role="user")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CompletionResponse
# ---------------------------------------------------------------------------

class TestCompletionResponse:
    def test_basic_creation(self):
        resp = CompletionResponse(
            content="The answer is 42.",
            model="gpt-4o",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        )
        assert resp.content == "The answer is 42."
        assert resp.model == "gpt-4o"
        assert resp.usage["total_tokens"] == 8
        assert resp.metadata is None

    def test_with_metadata(self):
        resp = CompletionResponse(
            content="x",
            model="m",
            usage={},
            metadata={"id": "abc", "stop_reason": "end_turn"},
        )
        assert resp.metadata["id"] == "abc"

    def test_usage_keys(self):
        usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        resp = CompletionResponse(content="y", model="m", usage=usage)
        assert resp.usage["prompt_tokens"] == 10
        assert resp.usage["completion_tokens"] == 20


# ---------------------------------------------------------------------------
# ImageResponse
# ---------------------------------------------------------------------------

class TestImageResponse:
    def test_basic_creation(self):
        img = ImageResponse(image_data="aGVsbG8=", model="dall-e-3")
        assert img.image_data == "aGVsbG8="
        assert img.model == "dall-e-3"
        assert img.revised_prompt is None
        assert img.metadata is None

    def test_with_revised_prompt(self):
        img = ImageResponse(
            image_data="data",
            model="dall-e-3",
            revised_prompt="A beautiful sunset",
        )
        assert img.revised_prompt == "A beautiful sunset"


# ---------------------------------------------------------------------------
# AudioResponse
# ---------------------------------------------------------------------------

class TestAudioResponse:
    def test_all_optional_fields_default_to_none(self):
        resp = AudioResponse()
        assert resp.audio_data is None
        assert resp.text is None
        assert resp.language is None
        assert resp.duration is None
        assert resp.model is None
        assert resp.metadata is None

    def test_tts_response(self):
        audio = AudioResponse(audio_data=b"\x00\x01\x02", model="tts-1")
        assert audio.audio_data == b"\x00\x01\x02"
        assert audio.model == "tts-1"

    def test_transcription_response(self):
        resp = AudioResponse(text="Hello world", language="en", duration=2.5)
        assert resp.text == "Hello world"
        assert resp.language == "en"
        assert resp.duration == 2.5


# ---------------------------------------------------------------------------
# VisionMessage
# ---------------------------------------------------------------------------

class TestVisionMessage:
    def test_with_image_url(self):
        msg = VisionMessage(role="user", text="What is this?", image_url="https://example.com/img.png")
        assert msg.role == "user"
        assert msg.text == "What is this?"
        assert msg.image_url == "https://example.com/img.png"
        assert msg.image_data is None

    def test_with_base64_image(self):
        msg = VisionMessage(role="user", text="Describe", image_data="aGVsbG8=")
        assert msg.image_data == "aGVsbG8="
        assert msg.image_url is None
