#!/usr/bin/env python3
"""
Ollama Provider Example

Demonstrates usage of the Ollama provider for local LLM inference.
Requires Ollama server running at http://localhost:11434

Install Ollama:
  curl https://ollama.ai/install.sh | sh

Pull a model:
  ollama pull llama3.2
  ollama pull llava  # For vision examples

Author: Luke Steuber
"""

import sys
sys.path.insert(0, '/home/coolhand/shared')

from llm_providers import ProviderFactory, Message
import base64


def example_basic_chat():
    """Example: Basic chat completion."""
    print("\n=== Basic Chat Completion ===")

    provider = ProviderFactory.get_provider('ollama')

    # Check if server is available
    status = provider.get_status()
    print(f"Ollama Status: {status['available']}")
    print(f"Available models: {status['models']}")

    if not status['available']:
        print("Error: Ollama server is not running")
        print("Start it with: ollama serve")
        return

    # Simple completion
    messages = [
        Message(role="system", content="You are a helpful assistant that answers concisely."),
        Message(role="user", content="Explain Python in one sentence.")
    ]

    response = provider.complete(messages, model='llama3.2', temperature=0.7)
    print(f"\nQuestion: {messages[1].content}")
    print(f"Answer: {response.content}")
    print(f"Tokens: {response.usage}")


def example_streaming():
    """Example: Streaming chat completion."""
    print("\n=== Streaming Completion ===")

    provider = ProviderFactory.get_provider('ollama')

    if not provider.available:
        print("Ollama server not available")
        return

    messages = [Message(role="user", content="Count from 1 to 5, one number per line.")]

    print("Streaming response:")
    for chunk in provider.stream_complete(messages, model='llama3.2'):
        if chunk.content:
            print(chunk.content, end='', flush=True)

        # Final chunk has usage stats
        if chunk.metadata and chunk.metadata.get('done'):
            print(f"\n\nTokens used: {chunk.usage}")


def example_vision():
    """Example: Vision/multimodal analysis."""
    print("\n=== Vision Analysis ===")

    provider = ProviderFactory.get_provider('ollama')

    if not provider.available:
        print("Ollama server not available")
        return

    # Check for vision models
    models = provider.get_model_metadata()
    vision_models = [m for m in models if 'vision' in m['metadata'].get('capabilities', [])]

    if not vision_models:
        print("No vision models available. Install one with: ollama pull llava")
        return

    print(f"Using vision model: {vision_models[0]['id']}")

    # For demo purposes, create a simple colored image
    try:
        from PIL import Image
        import io

        # Create a simple red square
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode()

        response = provider.analyze_image(
            image=img_base64,
            prompt="What color is this image?",
            model=vision_models[0]['id']
        )

        print(f"Question: What color is this image?")
        print(f"Answer: {response.content}")
        print(f"Tokens: {response.usage}")

    except ImportError:
        print("PIL not available for image generation")


def example_model_comparison():
    """Example: Compare different models."""
    print("\n=== Model Comparison ===")

    provider = ProviderFactory.get_provider('ollama')

    if not provider.available:
        print("Ollama server not available")
        return

    models = provider.list_models()
    if len(models) < 1:
        print("No models available. Pull one with: ollama pull llama3.2")
        return

    print(f"Available models: {models}")

    # Test with different models
    question = Message(role="user", content="What is 2+2?")

    for model in models[:2]:  # Test first 2 models
        print(f"\nTesting model: {model}")
        try:
            response = provider.complete([question], model=model)
            print(f"Response: {response.content[:100]}")
            print(f"Tokens: {response.usage['total_tokens']}")
        except Exception as e:
            print(f"Error: {e}")


def example_factory_integration():
    """Example: Using ProviderFactory features."""
    print("\n=== Factory Integration ===")

    # Check capabilities
    from llm_providers import PROVIDER_CAPABILITIES

    ollama_caps = PROVIDER_CAPABILITIES['ollama']
    print("Ollama capabilities:")
    for cap, supported in ollama_caps.items():
        status = "✓" if supported else "✗"
        print(f"  {status} {cap}")

    # Get provider via factory
    provider = ProviderFactory.get_provider('ollama')
    print(f"\nProvider instance: {provider.__class__.__name__}")
    print(f"Default model: {provider.model}")

    # Create custom instance
    custom_provider = ProviderFactory.create_provider(
        'ollama',
        api_key='not-used',  # Ollama doesn't need API key
        model='llama3.2'
    )
    print(f"Custom instance model: {custom_provider.model}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Ollama Provider Examples")
    print("=" * 60)

    try:
        example_basic_chat()
        example_streaming()
        example_model_comparison()
        example_factory_integration()
        example_vision()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
