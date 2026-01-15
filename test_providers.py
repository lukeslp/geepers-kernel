#!/usr/bin/env python3
"""
Test script for all LLM providers in the shared library.
Tests basic connectivity and API functionality.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import providers
from llm_providers import Message
from llm_providers.anthropic_provider import AnthropicProvider
from llm_providers.openai_provider import OpenAIProvider
from llm_providers.xai_provider import XAIProvider
from llm_providers.mistral_provider import MistralProvider
from llm_providers.cohere_provider import CohereProvider
from llm_providers.gemini_provider import GeminiProvider
from llm_providers.perplexity_provider import PerplexityProvider


def test_provider(name: str, provider_class, api_key_env: str):
    """Test a single provider."""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")

    # Check if API key exists
    api_key = os.getenv(api_key_env)
    if not api_key:
        print(f"❌ SKIPPED: {api_key_env} not set")
        return False

    try:
        # Initialize provider
        provider = provider_class(api_key=api_key)
        print(f"✅ Provider initialized")

        # Test model listing
        try:
            models = provider.list_models()
            print(f"✅ Models listed: {len(models)} models")
            print(f"   Sample models: {', '.join(models[:3])}")
        except Exception as e:
            print(f"⚠️  Model listing failed: {e}")

        # Test simple completion
        messages = [Message(role="user", content="Say 'test successful' and nothing else")]
        response = provider.complete(messages, max_tokens=10)
        print(f"✅ Completion successful")
        print(f"   Response: {response.content}")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage['total_tokens']}")

        # Test streaming
        print(f"✅ Testing streaming...")
        stream_response = ""
        for chunk in provider.stream_complete(messages, max_tokens=10):
            stream_response += chunk
        print(f"   Streaming response: {stream_response}")

        print(f"\n✅ {name} - ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ {name} - FAILED: {e}")
        return False


def main():
    """Run all provider tests."""
    print("="*60)
    print("SHARED LIBRARY PROVIDER TESTS")
    print("="*60)

    providers = [
        ("Anthropic (Claude)", AnthropicProvider, "ANTHROPIC_API_KEY"),
        ("OpenAI (GPT)", OpenAIProvider, "OPENAI_API_KEY"),
        ("xAI (Grok)", XAIProvider, "XAI_API_KEY"),
        ("Mistral", MistralProvider, "MISTRAL_API_KEY"),
        ("Cohere", CohereProvider, "COHERE_API_KEY"),
        ("Google Gemini", GeminiProvider, "GEMINI_API_KEY"),
        ("Perplexity", PerplexityProvider, "PERPLEXITY_API_KEY"),
    ]

    results = {}
    for name, provider_class, api_key_env in providers:
        results[name] = test_provider(name, provider_class, api_key_env)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    sum(1 for v in results.values() if v is None)

    for name, result in results.items():
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⊘ SKIP"
        print(f"{status} - {name}")

    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed} | Skipped: {len(results) - passed - failed}")

    # Exit with error if any tests failed
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
