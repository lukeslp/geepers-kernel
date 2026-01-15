"""
Tests for embedding utilities.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch
from shared.utils.embeddings import (
    EmbeddingGenerator,
    EmbeddingResult,
    SimilarityResult,
    calculate_similarity,
    find_most_similar,
    embedding_to_bytes,
    bytes_to_embedding,
    generate_embedding,
    generate_batch_embeddings
)


class TestEmbeddingResult:
    """Test EmbeddingResult dataclass."""

    @pytest.fixture
    def numpy_available(self):
        """Check if numpy is available."""
        try:
            return True
        except ImportError:
            pytest.skip("numpy not installed")

    def test_embedding_result_success(self, numpy_available):
        """Test successful EmbeddingResult."""
        embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        result = EmbeddingResult(
            embedding=embedding,
            model="nomic-embed-text",
            provider="ollama",
            dimensions=3,
            success=True
        )

        assert result.success is True
        assert result.dimensions == 3
        assert result.error is None

    def test_embedding_result_error(self, numpy_available):
        """Test EmbeddingResult with error."""
        result = EmbeddingResult(
            embedding=None,
            model="test-model",
            provider="test",
            success=False,
            error="API error"
        )

        assert result.success is False
        assert result.error == "API error"


class TestSimilarityResult:
    """Test SimilarityResult dataclass."""

    def test_similarity_result_structure(self):
        """Test SimilarityResult has expected attributes."""
        result = SimilarityResult(
            text="Example text",
            score=0.95,
            index=0,
            metadata={"source": "test"}
        )

        assert result.text == "Example text"
        assert result.score == 0.95
        assert result.index == 0


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""

    @pytest.fixture
    def numpy_available(self):
        """Check if numpy is available."""
        try:
            return True
        except ImportError:
            pytest.skip("numpy not installed")

    def test_init_ollama_provider(self, numpy_available):
        """Test initialization with Ollama provider."""
        with patch('shared.utils.embeddings.OLLAMA_AVAILABLE', True):
            generator = EmbeddingGenerator(
                provider="ollama",
                model="nomic-embed-text"
            )
            assert generator.provider == "ollama"
            assert generator.model == "nomic-embed-text"

    def test_init_openai_provider(self, numpy_available):
        """Test initialization with OpenAI provider."""
        with patch('shared.utils.embeddings.OPENAI_AVAILABLE', True):
            with patch('shared.utils.embeddings.OpenAI') as mock_openai:
                generator = EmbeddingGenerator(
                    provider="openai",
                    model="text-embedding-ada-002",
                    api_key="test-key"
                )
                assert generator.provider == "openai"
                assert mock_openai.called

    def test_init_invalid_provider(self, numpy_available):
        """Test initialization with invalid provider."""
        with pytest.raises(ValueError, match="Unknown provider"):
            EmbeddingGenerator(provider="invalid", api_key="test")

    def test_init_openai_without_key(self, numpy_available):
        """Test OpenAI provider without API key raises error."""
        with patch('shared.utils.embeddings.OPENAI_AVAILABLE', True):
            with patch.dict('os.environ', {}, clear=True):
                with pytest.raises(ValueError, match="OPENAI_API_KEY required"):
                    EmbeddingGenerator(provider="openai")

    @patch('shared.utils.embeddings.ollama')
    def test_generate_with_ollama(self, mock_ollama, numpy_available):
        """Test embedding generation with Ollama."""
        with patch('shared.utils.embeddings.OLLAMA_AVAILABLE', True):
            # Mock Ollama response
            mock_ollama.embed.return_value = {
                "embeddings": [[0.1, 0.2, 0.3]]
            }

            generator = EmbeddingGenerator(provider="ollama", model="nomic-embed-text")
            result = generator.generate("Hello world")

            assert result.success is True
            assert result.embedding is not None
            assert result.dimensions == 3

    @patch('shared.utils.embeddings.OpenAI')
    def test_generate_with_openai(self, mock_openai_class, numpy_available):
        """Test embedding generation with OpenAI."""
        with patch('shared.utils.embeddings.OPENAI_AVAILABLE', True):
            # Mock OpenAI client
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
            mock_client.embeddings.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            generator = EmbeddingGenerator(
                provider="openai",
                model="text-embedding-ada-002",
                api_key="test-key"
            )
            result = generator.generate("Hello world")

            assert result.success is True
            assert result.embedding is not None

    @patch('shared.utils.embeddings.ollama')
    def test_generate_batch(self, mock_ollama, numpy_available):
        """Test batch embedding generation."""
        with patch('shared.utils.embeddings.OLLAMA_AVAILABLE', True):
            mock_ollama.embed.return_value = {
                "embeddings": [[0.1, 0.2, 0.3]]
            }

            generator = EmbeddingGenerator(provider="ollama")
            results = generator.generate_batch(["Hello", "World"])

            assert len(results) == 2
            assert all(r.success for r in results)


class TestSimilarityFunctions:
    """Test similarity calculation functions."""

    @pytest.fixture
    def numpy_available(self):
        """Check if numpy is available."""
        try:
            return True
        except ImportError:
            pytest.skip("numpy not installed")

    def test_calculate_similarity_identical(self, numpy_available):
        """Test similarity of identical vectors."""
        emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        emb2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        similarity = calculate_similarity(emb1, emb2)
        assert abs(similarity - 1.0) < 0.001

    def test_calculate_similarity_orthogonal(self, numpy_available):
        """Test similarity of orthogonal vectors."""
        emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        emb2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        similarity = calculate_similarity(emb1, emb2)
        assert abs(similarity - 0.0) < 0.001

    def test_calculate_similarity_opposite(self, numpy_available):
        """Test similarity of opposite vectors."""
        emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        emb2 = np.array([-1.0, 0.0, 0.0], dtype=np.float32)

        similarity = calculate_similarity(emb1, emb2)
        assert abs(similarity - (-1.0)) < 0.001

    def test_find_most_similar(self, numpy_available):
        """Test finding most similar embeddings."""
        query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        candidates = [
            np.array([1.0, 0.0, 0.0], dtype=np.float32),  # Most similar
            np.array([0.5, 0.5, 0.0], dtype=np.float32),  # Somewhat similar
            np.array([0.0, 1.0, 0.0], dtype=np.float32),  # Orthogonal
        ]
        texts = ["Identical", "Similar", "Different"]

        results = find_most_similar(query, candidates, texts, top_k=2)

        assert len(results) == 2
        assert results[0].text == "Identical"
        assert results[0].score > results[1].score

    def test_find_most_similar_without_texts(self, numpy_available):
        """Test finding most similar without text labels."""
        query = np.array([1.0, 0.0], dtype=np.float32)
        candidates = [
            np.array([1.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0], dtype=np.float32),
        ]

        results = find_most_similar(query, candidates, top_k=2)

        assert len(results) == 2
        assert "Item 0" in results[0].text


class TestVectorSerialization:
    """Test vector serialization functions."""

    @pytest.fixture
    def numpy_available(self):
        """Check if numpy is available."""
        try:
            return True
        except ImportError:
            pytest.skip("numpy not installed")

    def test_embedding_to_bytes(self, numpy_available):
        """Test converting embedding to bytes."""
        emb = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        blob = embedding_to_bytes(emb)

        assert isinstance(blob, bytes)
        assert len(blob) == 12  # 3 floats * 4 bytes

    def test_bytes_to_embedding(self, numpy_available):
        """Test converting bytes back to embedding."""
        original = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        blob = embedding_to_bytes(original)
        restored = bytes_to_embedding(blob)

        assert np.allclose(original, restored)

    def test_roundtrip_serialization(self, numpy_available):
        """Test full roundtrip serialization."""
        original = np.array([0.123, 0.456, 0.789], dtype=np.float32)
        blob = embedding_to_bytes(original)
        restored = bytes_to_embedding(blob)

        similarity = calculate_similarity(original, restored)
        assert abs(similarity - 1.0) < 0.001


class TestFunctionalInterface:
    """Test functional interface convenience functions."""

    @pytest.fixture
    def numpy_available(self):
        """Check if numpy is available."""
        try:
            return True
        except ImportError:
            pytest.skip("numpy not installed")

    @patch('shared.utils.embeddings.EmbeddingGenerator')
    def test_generate_embedding_function(self, mock_generator_class, numpy_available):
        """Test generate_embedding convenience function."""
        mock_generator = Mock()
        mock_result = EmbeddingResult(
            embedding=np.array([0.1, 0.2, 0.3]),
            model="test",
            provider="ollama",
            success=True
        )
        mock_generator.generate.return_value = mock_result
        mock_generator_class.return_value = mock_generator

        result = generate_embedding("Hello", api_key="test")

        assert result is not None
        assert mock_generator.generate.called

    @patch('shared.utils.embeddings.EmbeddingGenerator')
    def test_generate_batch_embeddings_function(self, mock_generator_class, numpy_available):
        """Test generate_batch_embeddings convenience function."""
        mock_generator = Mock()
        mock_results = [
            EmbeddingResult(
                embedding=np.array([0.1, 0.2]),
                model="test",
                provider="ollama",
                success=True
            ),
            EmbeddingResult(
                embedding=np.array([0.3, 0.4]),
                model="test",
                provider="ollama",
                success=True
            )
        ]
        mock_generator.generate_batch.return_value = mock_results
        mock_generator_class.return_value = mock_generator

        results = generate_batch_embeddings(["Hello", "World"], api_key="test")

        assert len(results) == 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def numpy_available(self):
        """Check if numpy is available."""
        try:
            return True
        except ImportError:
            pytest.skip("numpy not installed")

    def test_invalid_similarity_method(self, numpy_available):
        """Test handling of invalid similarity method."""
        emb1 = np.array([1.0, 0.0])
        emb2 = np.array([0.0, 1.0])

        with pytest.raises(ValueError, match="Unknown similarity method"):
            calculate_similarity(emb1, emb2, method="invalid")

    @patch('shared.utils.embeddings.ollama')
    def test_api_error_handling(self, mock_ollama, numpy_available):
        """Test handling of API errors."""
        with patch('shared.utils.embeddings.OLLAMA_AVAILABLE', True):
            mock_ollama.embed.side_effect = Exception("API Error")

            generator = EmbeddingGenerator(provider="ollama")
            result = generator.generate("Hello")

            assert result.success is False
            assert "API Error" in result.error
