from __future__ import annotations

import asyncio
import pytest

from shared.utils import (
    async_retry,
    chunk_text,
    coerce_types,
    derive_key,
    ensure_fields,
    generate_hmac,
    generate_outline,
    hash_text,
    InMemoryRateLimiter,
    normalize_whitespace,
    retry,
    split_into_sentences,
    TokenBucket,
    ValidationError,
    validate_choices,
    validate_schema,
    extract_keywords,
    FERNET_AVAILABLE,
    generate_random_key,
    encrypt_text,
    decrypt_text,
    generate_symmetric_key,
)


def test_text_processing_helpers():
    raw = "Hello\u00a0world!  This   is\na\ttest."
    normalized = normalize_whitespace(raw)
    assert normalized == "Hello world! This is a test."

    sentences = split_into_sentences("One. Two three four five. Six.", max_length=6)
    assert sentences == ["One.", "Two three", "four five.", "Six."]

    chunks = chunk_text("Sentence one. Sentence two. Sentence three.", chunk_size=20, overlap=5)
    assert chunks[0].startswith("Sentence one")
    assert len(chunks) >= 2

    keywords = extract_keywords("alpha beta beta gamma gamma gamma", top_k=2)
    assert keywords == [("gamma", 3), ("beta", 2)]

    outline = generate_outline("# Title\n## Section\nContent", max_depth=2)
    assert outline == ["- Title", "-- Section"]


def test_data_validation_helpers():
    data = {"name": "Demo", "status": "active", "count": "10"}
    ensure_fields(data, ["name", "status"])
    with pytest.raises(ValidationError):
        ensure_fields(data, ["missing"])

    validate_choices(data, "status", ["active", "inactive"])
    with pytest.raises(ValidationError):
        validate_choices(data, "status", ["inactive"])

    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string", "minLength": 2},
            "count": {"type": "number", "minimum": 0},
        },
    }
    errors = validate_schema({"name": "A", "count": -1}, schema)
    assert len(errors) == 2

    coerced = coerce_types(data, {"count": int})
    assert coerced["count"] == 10


def test_retry_helpers():
    attempts = {"count": 0}

    @retry(max_attempts=3, delay=0.01)
    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("fail")
        return "ok"

    assert flaky() == "ok"
    assert attempts["count"] == 2

    async_attempts = {"count": 0}

    @async_retry(max_attempts=3, delay=0.01)
    async def async_flaky():
        async_attempts["count"] += 1
        if async_attempts["count"] < 2:
            raise RuntimeError("fail")
        return "ok"

    result = asyncio.run(async_flaky())
    assert result == "ok"
    assert async_attempts["count"] == 2


def test_rate_limiter():
    bucket = TokenBucket(capacity=1, refill_rate=100, tokens=1)
    assert bucket.consume()
    assert not bucket.consume()

    limiter = InMemoryRateLimiter()
    limiter.register_bucket("test", capacity=2, refill_rate=100)

    assert limiter.check("test")
    assert limiter.check("test")
    assert not limiter.check("test")


def test_crypto_helpers():
    h1 = hash_text("demo")
    h2 = hash_text("demo")
    assert h1 == h2

    sig = generate_hmac("payload", "secret")
    assert generate_hmac("payload", "secret") == sig
    assert generate_hmac("payload", "secret2") != sig

    key_hex, salt_hex = derive_key("password")
    assert len(key_hex) == 64
    assert len(salt_hex) == 32

    random_key = generate_random_key(32)
    assert len(random_key) >= 32

    if FERNET_AVAILABLE:
        key = generate_symmetric_key()
        encrypted = encrypt_text("hello", key)
        decrypted = decrypt_text(encrypted, key)
        assert decrypted == "hello"
    else:
        with pytest.raises(RuntimeError):
            encrypt_text("hello", "invalid")

