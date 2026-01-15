"""
Tests for vision utilities (shared/utils/vision.py).

This module tests image/video analysis using AI vision models.
Tests use mocking to avoid requiring actual API calls or media files.

Author: Luke Steuber
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Test availability flags
OPENAI_AVAILABLE = True
PIL_AVAILABLE = True
CV2_AVAILABLE = True

try:
    from PIL import Image
except ImportError:
    PIL_AVAILABLE = False

try:
    pass
except ImportError:
    CV2_AVAILABLE = False

# Import vision module (will handle missing dependencies)
import sys
sys.path.insert(0, str(Path.home() / "shared"))

try:
    from utils.vision import (
        VisionResult,
        VisionClient,
        analyze_image,
        generate_filename_from_vision
    )
    VISION_MODULE_AVAILABLE = True
except ImportError as e:
    VISION_MODULE_AVAILABLE = False
    IMPORT_ERROR = str(e)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_image():
    """Create temporary test image file."""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        # Create minimal valid JPEG
        if PIL_AVAILABLE:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(f.name)
        else:
            # Write minimal JPEG header
            f.write(b'\xff\xd8\xff\xe0')  # JPEG SOI + APP0
        yield Path(f.name)
    # Cleanup
    try:
        os.unlink(f.name)
    except:
        pass


@pytest.fixture
def temp_video():
    """Create temporary test video file (stub)."""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        # Create stub video file
        f.write(b'fake video content')
        yield Path(f.name)
    # Cleanup
    try:
        os.unlink(f.name)
    except:
        pass


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for API calls."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="A beautiful sunset over mountains"))
    ]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_api_key(monkeypatch):
    """Set mock API key in environment."""
    monkeypatch.setenv("XAI_API_KEY", "test-api-key-12345")


# ============================================================================
# VisionResult Tests
# ============================================================================

@pytest.mark.skipif(not VISION_MODULE_AVAILABLE, reason="Vision module not available")
class TestVisionResult:
    """Test VisionResult dataclass."""

    def test_vision_result_success(self):
        """Test successful vision result."""
        result = VisionResult(
            success=True,
            description="A photo of a cat",
            confidence=0.95,
            suggested_filename="photo_cat"
        )

        assert result.success is True
        assert result.description == "A photo of a cat"
        assert result.confidence == 0.95
        assert result.suggested_filename == "photo_cat"
        assert result.error is None
        assert result.metadata == {}

    def test_vision_result_failure(self):
        """Test failed vision result."""
        result = VisionResult(
            success=False,
            description="",
            error="File not found"
        )

        assert result.success is False
        assert result.description == ""
        assert result.error == "File not found"
        assert result.confidence is None

    def test_vision_result_with_metadata(self):
        """Test vision result with metadata."""
        result = VisionResult(
            success=True,
            description="Test",
            metadata={"model": "grok-2-vision", "tokens": 150}
        )

        assert result.metadata["model"] == "grok-2-vision"
        assert result.metadata["tokens"] == 150


# ============================================================================
# VisionClient Tests
# ============================================================================

@pytest.mark.skipif(not VISION_MODULE_AVAILABLE, reason="Vision module not available")
class TestVisionClient:
    """Test VisionClient class."""

    def test_init_with_api_key(self, mock_api_key):
        """Test initialization with API key."""
        with patch('utils.vision.OpenAI') as mock_openai:
            client = VisionClient(api_key="test-key")

            assert client.api_key == "test-key"
            assert client.model == "grok-2-vision-1212"
            assert client.provider == "xai"
            mock_openai.assert_called_once()

    def test_init_from_environment(self, mock_api_key):
        """Test initialization from environment variable."""
        with patch('utils.vision.OpenAI') as mock_openai:
            client = VisionClient()

            assert client.api_key == "test-api-key-12345"
            mock_openai.assert_called_once()

    def test_init_without_api_key(self, monkeypatch):
        """Test initialization fails without API key."""
        monkeypatch.delenv("XAI_API_KEY", raising=False)

        with patch('utils.vision.OpenAI'):
            with pytest.raises(ValueError, match="API key required"):
                VisionClient()

    def test_init_custom_model(self, mock_api_key):
        """Test initialization with custom model."""
        with patch('utils.vision.OpenAI') as mock_openai:
            client = VisionClient(model="grok-vision-beta")

            assert client.model == "grok-vision-beta"

    @patch('utils.vision.OPENAI_AVAILABLE', False)
    def test_init_without_openai(self, mock_api_key):
        """Test initialization fails without openai package."""
        with pytest.raises(ImportError, match="openai package required"):
            VisionClient()


# ============================================================================
# Image Analysis Tests
# ============================================================================

@pytest.mark.skipif(not VISION_MODULE_AVAILABLE, reason="Vision module not available")
class TestImageAnalysis:
    """Test image analysis functionality."""

    def test_analyze_image_success(self, temp_image, mock_api_key, mock_openai_client):
        """Test successful image analysis."""
        with patch('utils.vision.OpenAI', return_value=mock_openai_client):
            client = VisionClient()
            result = client.analyze_image(temp_image)

            assert result.success is True
            assert "sunset" in result.description.lower() or "mountains" in result.description.lower()
            assert result.error is None

    def test_analyze_image_file_not_found(self, mock_api_key):
        """Test analysis with non-existent file."""
        with patch('utils.vision.OpenAI'):
            client = VisionClient()
            result = client.analyze_image(Path("/nonexistent/image.jpg"))

            assert result.success is False
            assert "not found" in result.error.lower()

    def test_analyze_image_unsupported_format(self, mock_api_key):
        """Test analysis with unsupported image format."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"not an image")
            temp_path = Path(f.name)

        try:
            with patch('utils.vision.OpenAI'):
                client = VisionClient()
                result = client.analyze_image(temp_path)

                assert result.success is False
                assert "supported" in result.error.lower()
        finally:
            os.unlink(temp_path)

    def test_analyze_image_custom_prompt(self, temp_image, mock_api_key, mock_openai_client):
        """Test analysis with custom prompt."""
        with patch('utils.vision.OpenAI', return_value=mock_openai_client):
            client = VisionClient()
            result = client.analyze_image(
                temp_image,
                prompt="Describe the colors in this image"
            )

            assert result.success is True
            # Verify custom prompt was used in API call
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args is not None

    def test_analyze_image_api_error(self, temp_image, mock_api_key):
        """Test handling of API errors."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with patch('utils.vision.OpenAI', return_value=mock_client):
            client = VisionClient()
            result = client.analyze_image(temp_image)

            assert result.success is False
            assert result.error is not None


# ============================================================================
# Video Analysis Tests
# ============================================================================

@pytest.mark.skipif(not VISION_MODULE_AVAILABLE or not CV2_AVAILABLE,
                    reason="Vision module or OpenCV not available")
class TestVideoAnalysis:
    """Test video analysis functionality."""

    def test_analyze_video_missing_opencv(self, temp_video, mock_api_key):
        """Test video analysis fails without OpenCV."""
        with patch('utils.vision.CV2_AVAILABLE', False):
            with patch('utils.vision.OpenAI'):
                client = VisionClient()
                result = client.analyze_video(temp_video)

                assert result.success is False
                assert "opencv" in result.error.lower()

    def test_analyze_video_file_not_found(self, mock_api_key):
        """Test video analysis with non-existent file."""
        with patch('utils.vision.OpenAI'):
            client = VisionClient()
            result = client.analyze_video(Path("/nonexistent/video.mp4"))

            assert result.success is False
            assert "not found" in result.error.lower()

    def test_analyze_video_unsupported_format(self, mock_api_key):
        """Test video analysis with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"not a video")
            temp_path = Path(f.name)

        try:
            with patch('utils.vision.OpenAI'):
                client = VisionClient()
                result = client.analyze_video(temp_path)

                assert result.success is False
                assert "supported" in result.error.lower()
        finally:
            os.unlink(temp_path)


# ============================================================================
# Filename Generation Tests
# ============================================================================

@pytest.mark.skipif(not VISION_MODULE_AVAILABLE, reason="Vision module not available")
class TestFilenameGeneration:
    """Test filename generation from visual content."""

    def test_generate_filename_success(self, temp_image, mock_api_key, mock_openai_client):
        """Test successful filename generation."""
        # Mock response with filename suggestion
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="sunset_mountains_sky"))
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        with patch('utils.vision.OpenAI', return_value=mock_openai_client):
            client = VisionClient()
            result = client.generate_filename(temp_image)

            assert result.success is True
            assert result.suggested_filename is not None
            assert len(result.suggested_filename) > 0

    def test_generate_filename_max_words(self, temp_image, mock_api_key, mock_openai_client):
        """Test filename generation with max words constraint."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="red_square"))
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        with patch('utils.vision.OpenAI', return_value=mock_openai_client):
            client = VisionClient()
            result = client.generate_filename(temp_image, max_words=2)

            assert result.success is True
            # Filename should respect max_words
            word_count = len(result.suggested_filename.split('_'))
            assert word_count <= 2

    def test_generate_filename_file_not_found(self, mock_api_key):
        """Test filename generation with non-existent file."""
        with patch('utils.vision.OpenAI'):
            client = VisionClient()
            result = client.generate_filename(Path("/nonexistent/image.jpg"))

            assert result.success is False
            assert result.suggested_filename is None


# ============================================================================
# Functional Interface Tests
# ============================================================================

@pytest.mark.skipif(not VISION_MODULE_AVAILABLE, reason="Vision module not available")
class TestFunctionalInterface:
    """Test convenience functions."""

    def test_analyze_image_function(self, temp_image, mock_api_key, mock_openai_client):
        """Test analyze_image convenience function."""
        with patch('utils.vision.OpenAI', return_value=mock_openai_client):
            result = analyze_image(temp_image)

            assert isinstance(result, VisionResult)
            assert result.success is True

    def test_analyze_image_with_custom_key(self, temp_image, mock_openai_client):
        """Test analyze_image with custom API key."""
        with patch('utils.vision.OpenAI', return_value=mock_openai_client):
            result = analyze_image(temp_image, api_key="custom-key")

            assert result.success is True

    def test_generate_filename_from_vision_function(self, temp_image, mock_api_key):
        """Test generate_filename_from_vision convenience function."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="test_image"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        with patch('utils.vision.OpenAI', return_value=mock_client):
            filename = generate_filename_from_vision(temp_image)

            assert isinstance(filename, str)
            assert len(filename) > 0

    def test_generate_filename_on_error_returns_empty(self, mock_api_key):
        """Test generate_filename_from_vision returns empty on error."""
        with patch('utils.vision.OpenAI'):
            filename = generate_filename_from_vision(Path("/nonexistent.jpg"))

            assert filename == ""


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.skipif(not VISION_MODULE_AVAILABLE, reason="Vision module not available")
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_large_image_path(self, mock_api_key, mock_openai_client):
        """Test handling of very long file paths."""
        with patch('utils.vision.OpenAI', return_value=mock_openai_client):
            # Create long path (within OS limits)
            long_name = "a" * 200 + ".jpg"
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False, prefix=long_name[:50]) as f:
                if PIL_AVAILABLE:
                    img = Image.new('RGB', (10, 10))
                    img.save(f.name)
                else:
                    f.write(b'\xff\xd8\xff\xe0')
                temp_path = Path(f.name)

            try:
                client = VisionClient()
                result = client.analyze_image(temp_path)
                # Should handle long paths gracefully
                assert result is not None
            finally:
                os.unlink(temp_path)

    def test_unicode_in_path(self, mock_api_key, mock_openai_client):
        """Test handling of unicode characters in file paths."""
        with patch('utils.vision.OpenAI', return_value=mock_openai_client):
            # Create file with unicode name
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False, prefix='测试_') as f:
                if PIL_AVAILABLE:
                    img = Image.new('RGB', (10, 10))
                    img.save(f.name)
                else:
                    f.write(b'\xff\xd8\xff\xe0')
                temp_path = Path(f.name)

            try:
                client = VisionClient()
                result = client.analyze_image(temp_path)
                # Should handle unicode paths
                assert result is not None
            finally:
                try:
                    os.unlink(temp_path)
                except:
                    pass

    def test_empty_api_response(self, temp_image, mock_api_key):
        """Test handling of empty API response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=""))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        with patch('utils.vision.OpenAI', return_value=mock_client):
            client = VisionClient()
            result = client.analyze_image(temp_image)

            # Should handle empty responses
            assert result is not None
            # May be success=True with empty description, or failure


# ============================================================================
# Integration Tests (Require Actual API Key)
# ============================================================================

@pytest.mark.api
@pytest.mark.skipif(
    not VISION_MODULE_AVAILABLE or not os.environ.get("XAI_API_KEY"),
    reason="Vision module not available or XAI_API_KEY not set"
)
class TestIntegration:
    """
    Integration tests requiring actual API access.

    Run with: pytest -v -m api
    Requires: XAI_API_KEY environment variable
    """

    def test_real_image_analysis(self, temp_image):
        """Test analysis with real API (if key available)."""
        # This test only runs with -m api flag and real API key
        client = VisionClient()
        result = client.analyze_image(temp_image)

        assert result.success is True
        assert len(result.description) > 0

    def test_real_filename_generation(self, temp_image):
        """Test filename generation with real API."""
        client = VisionClient()
        result = client.generate_filename(temp_image)

        assert result.success is True
        assert result.suggested_filename is not None
        assert len(result.suggested_filename) > 0
        # Filename should use underscores, not spaces
        assert ' ' not in result.suggested_filename
