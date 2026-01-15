"""
Text processing utilities for cleaning, chunking, and summarising content.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List, Optional, Tuple

__all__ = [
    "DEFAULT_STOPWORDS",
    "normalize_whitespace",
    "split_into_sentences",
    "chunk_text",
    "extract_keywords",
    "generate_outline",
]

DEFAULT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


def normalize_whitespace(text: str) -> str:
    """
    Collapse repeated whitespace, convert smart quotes, and strip leading/trailing space.

    Args:
        text: Raw input text.

    Returns:
        Cleaned text with consistent whitespace.
    """
    if not text:
        return ""

    replacements = {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u00a0": " ",
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)

    collapsed = re.sub(r"\s+", " ", text)
    return collapsed.strip()


def split_into_sentences(text: str, max_length: int = 500) -> List[str]:
    """
    Split text into approximate sentences while respecting a maximum length.

    Args:
        text: Input text.
        max_length: Maximum length for each sentence chunk.

    Returns:
        List of sentence-like chunks.
    """
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []

    sentence_endings = re.compile(r"(?<=[.!?])\s+")
    sentences = sentence_endings.split(cleaned)
    combined: List[str] = []
    buffer = ""

    for sentence in sentences:
        candidate = (buffer + " " + sentence).strip() if buffer else sentence
        if len(candidate) <= max_length:
            buffer = candidate
        else:
            if buffer:
                combined.append(buffer)
            if len(sentence) <= max_length:
                buffer = sentence
            else:
                combined.extend(_chunk_long_sentence(sentence, max_length))
                buffer = ""

    if buffer:
        combined.append(buffer)
    return combined


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
    sentence_max: int = 500,
) -> List[str]:
    """
    Chunk text into overlapping windows suitable for LLM prompts.

    Args:
        text: Input text.
        chunk_size: Target length for each chunk.
        overlap: Number of characters to overlap between chunks.
        sentence_max: Maximum sentence length for pre-splitting.

    Returns:
        List of chunks.
    """
    sentences = split_into_sentences(text, max_length=sentence_max)
    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            if len(sentence) > chunk_size:
                chunks.extend(_chunk_long_sentence(sentence, chunk_size))
                current = ""
            else:
                current = sentence

    if current:
        chunks.append(current)

    if overlap > 0 and len(chunks) > 1:
        overlapped: List[str] = []
        for idx, chunk in enumerate(chunks):
            if idx == 0:
                overlapped.append(chunk)
                continue
            previous = overlapped[-1]
            overlap_text = previous[-overlap:] if len(previous) > overlap else previous
            overlapped.append((overlap_text + " " + chunk).strip())
        return overlapped

    return chunks


def extract_keywords(
    text: str,
    *,
    top_k: int = 10,
    stopwords: Optional[Iterable[str]] = None,
) -> List[Tuple[str, int]]:
    """
    Extract simple keyword frequencies using a bag-of-words approach.

    Args:
        text: Input text.
        top_k: Number of keywords to return.
        stopwords: Optional custom stopword list.

    Returns:
        List of (keyword, frequency) tuples sorted by frequency then alphabetically.
    """
    stopword_set = set(stopwords or DEFAULT_STOPWORDS)
    tokens = re.findall(r"[a-zA-Z0-9']+", text.lower())

    counts = Counter(token for token in tokens if token not in stopword_set and len(token) > 2)
    most_common = counts.most_common(top_k)
    return most_common


def generate_outline(
    text: str,
    *,
    max_depth: int = 2,
    heading_pattern: str = r"^#+\s",
    bullet: str = "-",
) -> List[str]:
    """
    Generate a Markdown outline from text headings or inferred sections.

    Args:
        text: Input Markdown or plain text.
        max_depth: Maximum heading depth to include.
        heading_pattern: Regex identifying headings (default Markdown style).
        bullet: Bullet symbol to use for outline items.

    Returns:
        List of outline lines.
    """
    lines = text.splitlines()
    outline: List[str] = []
    heading_regex = re.compile(heading_pattern)

    for line in lines:
        if heading_regex.match(line):
            depth = line.count("#")
            if depth <= max_depth:
                title = heading_regex.sub("", line).strip()
                outline.append(f"{bullet * depth} {title}")
        elif not outline and line.strip():
            # Fallback: infer first non-empty line as top-level heading
            outline.append(f"{bullet} {line.strip()}")

    return outline


def _chunk_long_sentence(sentence: str, max_length: int) -> List[str]:
    """Chunk a single sentence that exceeds the maximum length."""
    words = sentence.split()
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for word in words:
        if current_len + len(word) + 1 <= max_length:
            current.append(word)
            current_len += len(word) + 1
        else:
            if current:
                chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)

    if current:
        chunks.append(" ".join(current))

    return chunks

