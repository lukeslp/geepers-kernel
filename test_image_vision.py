#!/usr/bin/env python3
"""
Comprehensive test suite for image generation and vision capabilities
in the shared LLM providers library.

Tests:
- OpenAI: DALL-E image generation, GPT-4 Vision
- xAI: Aurora image generation, Grok Vision
- Anthropic: Claude Vision (no image generation)
"""

import os
import sys
import base64
from pathlib import Path

# Add shared to path for testing
sys.path.insert(0, str(Path(__file__).parent))

from llm_providers.openai_provider import OpenAIProvider
from llm_providers.xai_provider import XAIProvider
from llm_providers.anthropic_provider import AnthropicProvider


def test_openai_image_generation():
    """Test OpenAI DALL-E image generation."""
    print("\n" + "="*60)
    print("Testing OpenAI DALL-E Image Generation")
    print("="*60)

    try:
        provider = OpenAIProvider()
        print(f"✓ OpenAI provider initialized")

        # Generate a simple image
        prompt = "A serene mountain landscape at sunset with a lake"
        print(f"Generating image: '{prompt}'")

        response = provider.generate_image(
            prompt=prompt,
            model="dall-e-3",
            size="1024x1024",
            quality="standard"
        )

        print(f"✓ Image generated successfully")
        print(f"  Model: {response.model}")
        print(f"  Image size: {len(response.image_data)} chars (base64)")
        if response.revised_prompt:
            print(f"  Revised prompt: {response.revised_prompt[:100]}...")

        # Save the image
        output_path = "/tmp/test_dalle_output.png"
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(response.image_data))
        print(f"✓ Image saved to {output_path}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_xai_image_generation():
    """Test xAI Aurora image generation."""
    print("\n" + "="*60)
    print("Testing xAI Aurora Image Generation")
    print("="*60)

    try:
        provider = XAIProvider()
        print(f"✓ xAI provider initialized")

        # Generate a simple image
        prompt = "A futuristic city with flying cars at night"
        print(f"Generating image: '{prompt}'")

        response = provider.generate_image(
            prompt=prompt,
            model="aurora"
        )

        print(f"✓ Image generated successfully")
        print(f"  Model: {response.model}")
        print(f"  Image size: {len(response.image_data)} chars (base64)")
        if response.metadata.get('url'):
            print(f"  Original URL: {response.metadata['url'][:60]}...")

        # Save the image
        output_path = "/tmp/test_aurora_output.png"
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(response.image_data))
        print(f"✓ Image saved to {output_path}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def create_test_image():
    """Create a simple test image (red square) for vision testing."""
    from PIL import Image
    import io

    # Create a 100x100 red square
    img = Image.new('RGB', (100, 100), color='red')

    # Add some text
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)
    try:
        # Try to use a font, fall back to default if not available
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()

    draw.text((10, 40), "TEST", fill='white', font=font)

    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()

    return img_bytes


def test_openai_vision():
    """Test OpenAI GPT-4 Vision."""
    print("\n" + "="*60)
    print("Testing OpenAI GPT-4 Vision")
    print("="*60)

    try:
        provider = OpenAIProvider()
        print(f"✓ OpenAI provider initialized")

        # Create test image
        img_bytes = create_test_image()
        print(f"✓ Created test image ({len(img_bytes)} bytes)")

        # Analyze the image
        prompt = "What do you see in this image? Describe the colors and any text."
        print(f"Analyzing with prompt: '{prompt}'")

        response = provider.analyze_image(
            image=img_bytes,
            prompt=prompt,
            model="gpt-4o"
        )

        print(f"✓ Analysis complete")
        print(f"  Model: {response.model}")
        print(f"  Response: {response.content[:200]}...")
        print(f"  Tokens used: {response.usage['total_tokens']}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_xai_vision():
    """Test xAI Grok Vision."""
    print("\n" + "="*60)
    print("Testing xAI Grok Vision")
    print("="*60)

    try:
        provider = XAIProvider()
        print(f"✓ xAI provider initialized")

        # Create test image
        img_bytes = create_test_image()
        print(f"✓ Created test image ({len(img_bytes)} bytes)")

        # Analyze the image
        prompt = "What do you see in this image? Describe the colors and any text."
        print(f"Analyzing with prompt: '{prompt}'")

        response = provider.analyze_image(
            image=img_bytes,
            prompt=prompt,
            model="grok-2-vision-1212"
        )

        print(f"✓ Analysis complete")
        print(f"  Model: {response.model}")
        print(f"  Response: {response.content[:200]}...")
        print(f"  Tokens used: {response.usage['total_tokens']}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_anthropic_vision():
    """Test Anthropic Claude Vision."""
    print("\n" + "="*60)
    print("Testing Anthropic Claude Vision")
    print("="*60)

    try:
        provider = AnthropicProvider()
        print(f"✓ Anthropic provider initialized")

        # Create test image
        img_bytes = create_test_image()
        print(f"✓ Created test image ({len(img_bytes)} bytes)")

        # Analyze the image
        prompt = "What do you see in this image? Describe the colors and any text."
        print(f"Analyzing with prompt: '{prompt}'")

        response = provider.analyze_image(
            image=img_bytes,
            prompt=prompt,
            model="claude-sonnet-4-5-20250929"
        )

        print(f"✓ Analysis complete")
        print(f"  Model: {response.model}")
        print(f"  Response: {response.content[:200]}...")
        print(f"  Tokens used: {response.usage['total_tokens']}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Shared Library Image Generation & Vision Test Suite")
    print("="*60)

    results = {}

    # Check for required packages
    print("\nChecking dependencies...")
    try:
        print("✓ Pillow installed")
    except ImportError:
        print("✗ Pillow not installed (pip install pillow)")
        return

    # Test image generation
    print("\n" + "="*60)
    print("IMAGE GENERATION TESTS")
    print("="*60)

    if os.getenv("OPENAI_API_KEY"):
        results['openai_image'] = test_openai_image_generation()
    else:
        print("\n⊘ Skipping OpenAI image generation (no API key)")
        results['openai_image'] = None

    if os.getenv("XAI_API_KEY"):
        results['xai_image'] = test_xai_image_generation()
    else:
        print("\n⊘ Skipping xAI image generation (no API key)")
        results['xai_image'] = None

    # Test vision capabilities
    print("\n" + "="*60)
    print("VISION ANALYSIS TESTS")
    print("="*60)

    if os.getenv("OPENAI_API_KEY"):
        results['openai_vision'] = test_openai_vision()
    else:
        print("\n⊘ Skipping OpenAI vision (no API key)")
        results['openai_vision'] = None

    if os.getenv("XAI_API_KEY"):
        results['xai_vision'] = test_xai_vision()
    else:
        print("\n⊘ Skipping xAI vision (no API key)")
        results['xai_vision'] = None

    if os.getenv("ANTHROPIC_API_KEY"):
        results['anthropic_vision'] = test_anthropic_vision()
    else:
        print("\n⊘ Skipping Anthropic vision (no API key)")
        results['anthropic_vision'] = None

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, result in results.items():
        if result is True:
            print(f"✓ {test_name}: PASSED")
        elif result is False:
            print(f"✗ {test_name}: FAILED")
        else:
            print(f"⊘ {test_name}: SKIPPED")

    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
