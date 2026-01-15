# API V3 Code Snippets

This directory contains reusable code snippets for the Camina API v3 implementation. These snippets are extracted from the v2 codebase and refactored for improved organization, maintainability, and clearer separation of concerns.

## Organization

The snippets are organized by functionality:

- `research.py` - Academic research API endpoints (Semantic Scholar, arXiv, PubMed)
- `tools.py` - Utility tools and AI function calling (archive retrieval, code execution, format conversion)
- `providers.py` - Provider factory pattern and base provider interface for AI models
- `ollama.py` - Ollama provider implementation for local LLM inference
- `chat.py` - Chat completion and streaming endpoints
- `utils.py` - Common utility functions used across the API
- `app.py` - Sample Flask application integrating all snippets

## Usage

These snippets are intended to be used as reference for implementing the v3 API. They contain the core functionality of the v2 API in a more modular and maintainable format.

### Integration Pattern

When implementing v3 APIs, follow this pattern:

1. Import the necessary classes and functions from the snippets
2. Create appropriate route handlers with consistent naming
3. Implement input validation, error handling, and authentication
4. Return standardized response formats

### Provider System

The provider system follows a factory pattern:

```python
# Register a provider
ProviderFactory.register_provider('provider_name', ProviderClass)

# Get a provider instance
provider = ProviderFactory.get_provider('provider_name')

# Use the provider
result = provider.chat_completion(prompt="Hello", model="model_name")
```

### Ollama Integration

The Ollama provider allows local LLM inference using [Ollama](https://github.com/ollama/ollama):

```python
# Register Ollama provider
from snippets.ollama import OllamaProvider
ProviderFactory.register_provider('ollama', OllamaProvider)

# Check Ollama connection
provider = ProviderFactory.get_provider('ollama')
status = provider.sample_request()
print(f"Ollama status: {status['status']}")

# List available models
models = provider.list_models()

# Use a model for completion
result = provider.chat_completion(
    prompt="What is machine learning?", 
    model="llama2"
)

# Multimodal inference with images
result = provider.chat_completion(
    prompt="Describe this image", 
    model="llava", 
    image_path="/path/to/image.jpg"
)
```

### Sample App

The sample app.py demonstrates how to integrate all snippets into a working Flask application:

```python
# Run the sample app
python snippets/app.py
```

This starts a server on port 8435 with all API routes available under `/api/v3/`.

## Key Improvements in v3

The v3 API design focuses on:

1. **Consistent Interface** - All endpoints use a standardized request/response format
2. **Better Documentation** - Comprehensive API docs using OpenAPI/Swagger
3. **Improved Error Handling** - Standardized error responses with clear messages
4. **Enhanced Authentication** - More robust and flexible authentication options
5. **Optimized Performance** - Better caching, async processing, and resource usage
6. **Comprehensive Testing** - Higher test coverage for all endpoints
7. **Accessibility Considerations** - Ensuring all APIs support accessibility needs
8. **Provider Abstraction** - Consistent interface for multiple AI providers
9. **Local LLM Support** - First-class support for local models via Ollama

## Dependencies

The snippets require the following dependencies:

- Flask - Web framework
- Requests - HTTP client
- PyYAML, toml - Format conversion
- WaybackPy, archiveis - Archive retrieval
- OpenAI, Anthropic, etc. - Provider-specific client libraries
- Ollama - Local LLM inference (optional)
- PIL/Pillow - Image processing for multimodal models

## Accessibility

When implementing v3 APIs based on these snippets, ensure:

1. All response formats include proper metadata for screen readers
2. Error messages are clear and descriptive
3. Rate limiting includes appropriate retry-after headers
4. Documentation includes accessibility considerations

## Troubleshooting

### Ollama Connection Issues

If you experience issues connecting to Ollama:

1. Ensure Ollama server is running: `ollama serve` in a terminal
2. Verify connection at http://localhost:11434
3. Check available models with `ollama list`
4. Use the `sample_request()` method to diagnose connection issues
5. Set custom host with environment variable: `export OLLAMA_HOST=http://your-server:11434`

## Contact

For questions or issues regarding these snippets, contact:
- Luke Steuber <api@assisted.space> 