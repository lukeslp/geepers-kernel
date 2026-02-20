#!/usr/bin/env python3
"""
Unified LLM Provider Ping Tool

Consolidates the following scattered utilities:
- projects/WORKING/ping_xai.py
- projects/WORKING/ping_openai.py
- projects/WORKING/ping_mistral.py
- projects/apis/cli_tools/ping_anthropic.py
- projects/apis/cli_tools/ping_cohere.py
- projects/apis/cli_tools/ping_gemini.py

Usage:
    python ping_providers.py --provider openai
    python ping_providers.py --provider anthropic
    python ping_providers.py --all
    python ping_providers.py --list
"""

import os
import sys
import argparse
from typing import Optional, Dict

# Provider configurations
PROVIDERS = {
    'openai': {
        'name': 'OpenAI',
        'env_key': 'OPENAI_API_KEY',
        'base_url': None,
        'package': 'openai',
    },
    'anthropic': {
        'name': 'Anthropic (Claude)',
        'env_key': 'ANTHROPIC_API_KEY',
        'base_url': None,
        'package': 'anthropic',
    },
    'xai': {
        'name': 'xAI (Grok)',
        'env_key': 'XAI_API_KEY',
        'base_url': 'https://api.x.ai/v1',
        'package': 'openai',
    },
    'mistral': {
        'name': 'Mistral AI',
        'env_key': 'MISTRAL_API_KEY',
        'base_url': 'https://api.mistral.ai/v1',
        'package': 'requests',
    },
    'cohere': {
        'name': 'Cohere',
        'env_key': 'COHERE_API_KEY',
        'base_url': 'https://api.cohere.ai/v1',
        'package': 'requests',
    },
    'gemini': {
        'name': 'Google Gemini',
        'env_key': 'GEMINI_API_KEY',
        'alt_env_key': 'GOOGLE_API_KEY',
        'base_url': 'https://generativelanguage.googleapis.com/v1beta',
        'package': 'requests',
    },
    'groq': {
        'name': 'Groq',
        'env_key': 'GROQ_API_KEY',
        'base_url': 'https://api.groq.com/openai/v1',
        'package': 'openai',
    },
    'perplexity': {
        'name': 'Perplexity',
        'env_key': 'PERPLEXITY_API_KEY',
        'base_url': 'https://api.perplexity.ai',
        'package': 'openai',
    },
}


def ping_openai_compatible(provider: str, api_key: str, base_url: Optional[str] = None) -> bool:
    """Ping OpenAI-compatible API."""
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: openai package not installed")
        return False
    
    config = PROVIDERS[provider]
    print(f"Connecting to {config['name']} API...")
    
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        models = client.models.list()
        
        print(f"SUCCESS: {config['name']} connected!")
        print(f"\nAvailable Models ({len(models.data)}):")
        print("-" * 50)
        
        for model in sorted(models.data, key=lambda x: x.id)[:15]:
            print(f"  - {model.id}")
        
        if len(models.data) > 15:
            print(f"  ... and {len(models.data) - 15} more")
        
        return True
    except Exception as e:
        print(f"FAILED: {config['name']} - {e}")
        return False


def ping_anthropic(api_key: str) -> bool:
    """Ping Anthropic API."""
    try:
        import anthropic
    except ImportError:
        print("Error: anthropic package not installed")
        return False
    
    print("Connecting to Anthropic API...")
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        models = client.models.list()
        claude_models = [m for m in models.data if m.id.startswith("claude")]
        
        print("SUCCESS: Anthropic connected!")
        print(f"\nAvailable Claude Models ({len(claude_models)}):")
        print("-" * 50)
        
        for model in sorted(claude_models, key=lambda x: x.id):
            print(f"  - {model.id}")
        
        return True
    except Exception as e:
        print(f"FAILED: Anthropic - {e}")
        return False


def ping_rest_api(provider: str, api_key: str) -> bool:
    """Ping REST-based APIs."""
    try:
        import requests
    except ImportError:
        print("Error: requests package not installed")
        return False
    
    config = PROVIDERS[provider]
    print(f"Connecting to {config['name']} API...")
    
    try:
        if provider == 'mistral':
            response = requests.get(
                f"{config['base_url']}/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
        elif provider == 'cohere':
            response = requests.get(
                f"{config['base_url']}/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
        elif provider == 'gemini':
            response = requests.get(
                f"{config['base_url']}/models?key={api_key}"
            )
        else:
            print(f"Unknown REST provider: {provider}")
            return False
        
        response.raise_for_status()
        data = response.json()
        
        print(f"SUCCESS: {config['name']} connected!")
        print("\nAvailable Models:")
        print("-" * 50)
        
        if provider == 'gemini':
            models = data.get('models', [])
            for model in models[:10]:
                name = model.get('name', '').replace('models/', '')
                print(f"  - {name}")
        else:
            models = data.get('data', data.get('models', []))
            for model in models[:10]:
                model_id = model.get('id', model.get('name', 'unknown'))
                print(f"  - {model_id}")
        
        return True
    except Exception as e:
        print(f"FAILED: {config['name']} - {e}")
        return False


def ping_provider(provider: str, api_key: Optional[str] = None) -> bool:
    """Ping a specific provider."""
    if provider not in PROVIDERS:
        print(f"Unknown provider: {provider}")
        print(f"Available: {', '.join(PROVIDERS.keys())}")
        return False
    
    config = PROVIDERS[provider]
    
    if not api_key:
        api_key = os.getenv(config['env_key'])
        if not api_key and 'alt_env_key' in config:
            api_key = os.getenv(config['alt_env_key'])
    
    if not api_key:
        print(f"No API key for {config['name']}.")
        print(f"Set {config['env_key']} environment variable.")
        return False
    
    if provider == 'anthropic':
        return ping_anthropic(api_key)
    elif config['package'] == 'openai':
        return ping_openai_compatible(provider, api_key, config.get('base_url'))
    else:
        return ping_rest_api(provider, api_key)


def ping_all() -> Dict[str, bool]:
    """Ping all configured providers."""
    results = {}
    
    print("=" * 60)
    print("PINGING ALL LLM PROVIDERS")
    print("=" * 60)
    
    for provider in PROVIDERS:
        print(f"\n{'-' * 60}")
        results[provider] = ping_provider(provider)
    
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print("=" * 60)
    
    success = sum(1 for r in results.values() if r)
    total = len(results)
    
    for provider, status in results.items():
        mark = "[OK]" if status else "[FAIL]"
        print(f"  {mark} {PROVIDERS[provider]['name']}")
    
    print(f"\n  {success}/{total} providers connected successfully")
    
    return results


def list_providers():
    """List all available providers."""
    print("Available LLM Providers:")
    print("-" * 50)
    
    for key, config in PROVIDERS.items():
        env_key = config['env_key']
        has_key = "[OK]" if os.getenv(env_key) else "[NO KEY]"
        print(f"  {has_key:10} {key:12} - {config['name']} ({env_key})")


def main():
    parser = argparse.ArgumentParser(description="Unified LLM Provider Ping Tool")
    parser.add_argument('--provider', '-p', choices=list(PROVIDERS.keys()), help='Provider to ping')
    parser.add_argument('--all', '-a', action='store_true', help='Ping all providers')
    parser.add_argument('--list', '-l', action='store_true', help='List available providers')
    parser.add_argument('--api-key', '-k', help='API key (overrides environment variable)')
    
    args = parser.parse_args()
    
    if args.list:
        list_providers()
    elif args.all:
        results = ping_all()
        sys.exit(0 if all(results.values()) else 1)
    elif args.provider:
        success = ping_provider(args.provider, args.api_key)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        print("\nTip: Use --list to see available providers")


if __name__ == "__main__":
    main()
