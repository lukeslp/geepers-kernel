"""
Embedding generation and semantic search utilities.

This module provides utilities for generating text embeddings and performing
semantic similarity search using various embedding providers (Ollama, OpenAI).

Features:
- Multi-provider support (Ollama, OpenAI, custom endpoints)
- Cosine similarity calculation
- Batch embedding generation
- Vector serialization (numpy arrays to/from bytes)
- Top-K similarity search
- Memory-efficient processing

Supported Providers:
- Ollama (local models like nomic-embed-text)
- OpenAI (text-embedding-ada-002, text-embedding-3-small)
- Custom endpoints (OpenAI-compatible APIs)

Usage:
    from shared.utils import generate_embedding, calculate_similarity

    # Generate embeddings
    embedding1 = generate_embedding("Hello world", model="nomic-embed-text")
    embedding2 = generate_embedding("Hi there", model="nomic-embed-text")

    # Calculate similarity
    similarity = calculate_similarity(embedding1, embedding2)
    print(f"Similarity: {similarity:.3f}")

Author: Luke Steuber
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

try:
    import numpy as np
    from numpy.linalg import norm as np_norm
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    np_norm = None
    NUMPY_AVAILABLE = False

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    ollama = None
    OLLAMA_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class EmbeddingResult:
    """
    Result from embedding generation.

    Attributes:
        embedding: Numpy array of embedding vector
        model: Model name used for embedding
        provider: Provider used (ollama, openai, custom)
        dimensions: Embedding dimensionality
        success: Whether generation succeeded
        error: Error message if failed
    """
    embedding: Optional['np.ndarray']
    model: str
    provider: str
    dimensions: Optional[int] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class SimilarityResult:
    """
    Result from similarity search.

    Attributes:
        text: Original text
        score: Similarity score (0-1, higher is more similar)
        index: Index in original list
        metadata: Optional additional metadata
    """
    text: str
    score: float
    index: int
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


# ============================================================================
# Embedding Generator
# ============================================================================

class EmbeddingGenerator:
    """
    Generate text embeddings using various providers.

    Example:
        >>> generator = EmbeddingGenerator(provider="ollama", model="nomic-embed-text")
        >>> result = generator.generate("Hello world")
        >>> print(result.dimensions)
        768
    """

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "nomic-embed-text:latest",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize embedding generator.

        Args:
            provider: Provider to use (ollama, openai, custom)
            model: Model name
            api_key: API key for OpenAI or custom provider
            base_url: Base URL for custom provider

        Raises:
            ImportError: If required libraries not installed
            ValueError: If provider invalid or credentials missing
        """
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy required. Install with: pip install numpy")

        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

        # Validate provider
        if self.provider == "ollama":
            if not OLLAMA_AVAILABLE:
                raise ImportError("ollama required. Install with: pip install ollama")
        elif self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai required. Install with: pip install openai")
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY required for OpenAI provider")
            self.client = OpenAI(api_key=self.api_key)
        elif self.provider == "custom":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai required for custom provider. Install with: pip install openai")
            if not self.api_key or not self.base_url:
                raise ValueError("api_key and base_url required for custom provider")
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'ollama', 'openai', or 'custom'")

        logger.info(f"Initialized EmbeddingGenerator: provider={provider}, model={model}")

    def generate(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with embedding vector

        Example:
            >>> result = generator.generate("Hello world")
            >>> print(result.embedding.shape)
            (768,)
        """
        try:
            if self.provider == "ollama":
                resp = ollama.embed(model=self.model, input=text)
                emb = resp["embeddings"]
                if isinstance(emb, list) and len(emb) > 0:
                    emb = emb[0] if isinstance(emb[0], list) else emb
                embedding = np.array(emb, dtype=np.float32)

            elif self.provider in {"openai", "custom"}:
                resp = self.client.embeddings.create(
                    input=text,
                    model=self.model
                )
                embedding = np.array(resp.data[0].embedding, dtype=np.float32)

            else:
                return EmbeddingResult(
                    embedding=None,
                    model=self.model,
                    provider=self.provider,
                    success=False,
                    error=f"Unsupported provider: {self.provider}"
                )

            logger.debug(f"Generated embedding: dim={embedding.shape[0]}")

            return EmbeddingResult(
                embedding=embedding,
                model=self.model,
                provider=self.provider,
                dimensions=embedding.shape[0],
                success=True
            )

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return EmbeddingResult(
                embedding=None,
                model=self.model,
                provider=self.provider,
                success=False,
                error=str(e)
            )

    def generate_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResult objects

        Example:
            >>> results = generator.generate_batch(["Hello", "World"])
            >>> print(len(results))
            2
        """
        results = []
        for text in texts:
            result = self.generate(text)
            results.append(result)
        return results


# ============================================================================
# Similarity Functions
# ============================================================================

def calculate_similarity(
    embedding1: 'np.ndarray',
    embedding2: 'np.ndarray',
    method: str = "cosine"
) -> float:
    """
    Calculate similarity between two embeddings.

    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        method: Similarity method (currently only 'cosine' supported)

    Returns:
        Similarity score (0-1, higher is more similar)

    Example:
        >>> emb1 = np.array([1.0, 0.0, 0.0])
        >>> emb2 = np.array([1.0, 0.0, 0.0])
        >>> similarity = calculate_similarity(emb1, emb2)
        >>> print(similarity)
        1.0
    """
    if not NUMPY_AVAILABLE:
        raise ImportError("numpy required. Install with: pip install numpy")

    if method == "cosine":
        # Cosine similarity: dot product / (norm1 * norm2)
        sim = np.dot(embedding1, embedding2) / (np_norm(embedding1) * np_norm(embedding2))
        # Convert to Python float if numpy scalar
        return sim.item() if hasattr(sim, "item") else float(sim)
    else:
        raise ValueError(f"Unknown similarity method: {method}")


def find_most_similar(
    query_embedding: 'np.ndarray',
    candidate_embeddings: List['np.ndarray'],
    candidate_texts: Optional[List[str]] = None,
    top_k: int = 5
) -> List[SimilarityResult]:
    """
    Find most similar embeddings to query.

    Args:
        query_embedding: Query embedding vector
        candidate_embeddings: List of candidate embeddings
        candidate_texts: Optional list of texts corresponding to candidates
        top_k: Number of top results to return

    Returns:
        List of SimilarityResult objects, sorted by score (descending)

    Example:
        >>> query = np.array([1.0, 0.0])
        >>> candidates = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
        >>> texts = ["Similar", "Different"]
        >>> results = find_most_similar(query, candidates, texts, top_k=2)
        >>> print(results[0].text, results[0].score)
        Similar 1.0
    """
    if not NUMPY_AVAILABLE:
        raise ImportError("numpy required. Install with: pip install numpy")

    # Calculate similarities
    similarities = []
    for i, candidate in enumerate(candidate_embeddings):
        score = calculate_similarity(query_embedding, candidate)
        text = candidate_texts[i] if candidate_texts else f"Item {i}"
        similarities.append(SimilarityResult(
            text=text,
            score=score,
            index=i
        ))

    # Sort by score (descending) and return top K
    similarities.sort(key=lambda x: x.score, reverse=True)
    return similarities[:top_k]


# ============================================================================
# Vector Serialization
# ============================================================================

def embedding_to_bytes(embedding: 'np.ndarray') -> bytes:
    """
    Convert embedding to bytes for storage.

    Args:
        embedding: Numpy array embedding

    Returns:
        Bytes representation

    Example:
        >>> emb = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        >>> blob = embedding_to_bytes(emb)
        >>> print(len(blob))
        12
    """
    if not NUMPY_AVAILABLE:
        raise ImportError("numpy required. Install with: pip install numpy")

    return embedding.tobytes()


def bytes_to_embedding(blob: bytes, dtype=None) -> 'np.ndarray':
    """
    Convert bytes back to embedding.

    Args:
        blob: Bytes representation
        dtype: Data type (default: np.float32)

    Returns:
        Numpy array embedding

    Example:
        >>> blob = b'\\x00\\x00\\x80?\\x00\\x00\\x00@\\x00\\x00@@'
        >>> emb = bytes_to_embedding(blob)
        >>> print(emb)
        [1. 2. 3.]
    """
    if not NUMPY_AVAILABLE:
        raise ImportError("numpy required. Install with: pip install numpy")

    if dtype is None:
        dtype = np.float32

    return np.frombuffer(blob, dtype=dtype)


# ============================================================================
# Functional Interface (Convenience Functions)
# ============================================================================

def generate_embedding(
    text: str,
    model: str = "nomic-embed-text:latest",
    provider: str = "ollama",
    api_key: Optional[str] = None
) -> 'np.ndarray':
    """
    Generate embedding for text (functional interface).

    Args:
        text: Text to embed
        model: Model name
        provider: Provider (ollama, openai, custom)
        api_key: API key for OpenAI/custom

    Returns:
        Numpy array embedding

    Raises:
        ValueError: If embedding generation fails

    Example:
        >>> from shared.utils import generate_embedding
        >>> emb = generate_embedding("Hello world")
        >>> print(emb.shape)
        (768,)
    """
    generator = EmbeddingGenerator(provider=provider, model=model, api_key=api_key)
    result = generator.generate(text)

    if not result.success:
        raise ValueError(f"Embedding generation failed: {result.error}")

    return result.embedding


def generate_batch_embeddings(
    texts: List[str],
    model: str = "nomic-embed-text:latest",
    provider: str = "ollama",
    api_key: Optional[str] = None
) -> List['np.ndarray']:
    """
    Generate embeddings for multiple texts (functional interface).

    Args:
        texts: List of texts to embed
        model: Model name
        provider: Provider (ollama, openai, custom)
        api_key: API key for OpenAI/custom

    Returns:
        List of numpy array embeddings

    Example:
        >>> embeddings = generate_batch_embeddings(["Hello", "World"])
        >>> print(len(embeddings))
        2
    """
    generator = EmbeddingGenerator(provider=provider, model=model, api_key=api_key)
    results = generator.generate_batch(texts)

    embeddings = []
    for result in results:
        if result.success:
            embeddings.append(result.embedding)
        else:
            logger.warning(f"Failed to generate embedding: {result.error}")
            embeddings.append(None)

    return embeddings


# ============================================================================
# Testing
# ============================================================================

def _test_embeddings():
    """Test function for standalone testing."""
    print("Testing Embedding Utilities...")
    print(f"NumPy available: {NUMPY_AVAILABLE}")
    print(f"Ollama available: {OLLAMA_AVAILABLE}")
    print(f"OpenAI available: {OPENAI_AVAILABLE}")

    if not NUMPY_AVAILABLE:
        print("\nERROR: numpy package required")
        print("Install with: pip install numpy")
        return

    if not OLLAMA_AVAILABLE:
        print("\nWARNING: ollama package not installed")
        print("Install with: pip install ollama")
        print("Skipping provider tests...")
        return

    print("\n1. Testing embedding generation...")
    try:
        generator = EmbeddingGenerator(provider="ollama", model="nomic-embed-text:latest")
        result = generator.generate("Hello world")

        if result.success:
            print(f"   ✓ Generated embedding: {result.dimensions} dimensions")
            print(f"     Model: {result.model}")
            print(f"     Provider: {result.provider}")
        else:
            print(f"   ✗ Failed: {result.error}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n2. Testing similarity calculation...")
    try:
        emb1 = generate_embedding("The cat sat on the mat")
        emb2 = generate_embedding("A feline rested on the rug")
        emb3 = generate_embedding("Python programming language")

        sim_12 = calculate_similarity(emb1, emb2)
        sim_13 = calculate_similarity(emb1, emb3)

        print(f"   Cat/Feline similarity: {sim_12:.3f}")
        print(f"   Cat/Python similarity: {sim_13:.3f}")
        print(f"   ✓ Cat more similar to Feline: {sim_12 > sim_13}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n3. Testing top-K search...")
    try:
        query = "machine learning"
        candidates = [
            "deep learning neural networks",
            "cooking recipes",
            "artificial intelligence",
            "gardening tips",
            "data science statistics"
        ]

        query_emb = generate_embedding(query)
        candidate_embs = generate_batch_embeddings(candidates)

        results = find_most_similar(query_emb, candidate_embs, candidates, top_k=3)

        print("   Top 3 similar to 'machine learning':")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result.text} ({result.score:.3f})")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n4. Testing serialization...")
    try:
        emb = generate_embedding("Test")
        blob = embedding_to_bytes(emb)
        restored = bytes_to_embedding(blob)

        similarity = calculate_similarity(emb, restored)
        print(f"   Original shape: {emb.shape}")
        print(f"   Blob size: {len(blob)} bytes")
        print(f"   Restored shape: {restored.shape}")
        print(f"   ✓ Similarity after roundtrip: {similarity:.3f}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\nAll tests complete!")


if __name__ == "__main__":
    _test_embeddings()
