# CLAUDE.md
<!-- Navigation: ~/shared/web/CLAUDE.md -->
<!-- Parent: ~/shared/CLAUDE.md -->
<!-- Map: ~/CLAUDE_MAP.md -->

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module: web

Shared web utilities and Flask components for building API proxies, web services, and RESTful endpoints.

### Overview

The web module provides:
- **Flask Blueprints** - Reusable API endpoints
- **LLM Proxy** - Unified proxy for LLM providers
- **Authentication** - Bearer token and signed token auth
- **CORS Configuration** - Cross-origin resource sharing
- **Rate Limiting** - API rate limiting middleware
- **Health Endpoints** - Service health checks
- **Vision Service** - Image processing utilities
- **Middleware** - Request logging, error handling, correlation IDs
- **Dreamwalker App** - Orchestrator web interface

### Quick Start

```python
from flask import Flask
from web import create_llm_proxy_app, setup_cors, create_health_endpoint

# Create Flask app with LLM proxy
app = create_llm_proxy_app()

# Add CORS
setup_cors(app)

# Add health endpoint
create_health_endpoint(app)

# Run
if __name__ == '__main__':
    app.run(port=5000)
```

### LLM Proxy Blueprint

Unified proxy for all LLM providers:

```python
from web import LLMProxyBlueprint, create_llm_proxy_app
from llm_providers import ProviderFactory

# Create blueprint
proxy = LLMProxyBlueprint(
    name='llm_proxy',
    providers={
        'openai': ProviderFactory.get_provider('openai'),
        'anthropic': ProviderFactory.get_provider('anthropic'),
        'xai': ProviderFactory.get_provider('xai')
    }
)

# Or use convenience function
app = create_llm_proxy_app(
    providers=['openai', 'anthropic', 'xai']
)

# Endpoints provided:
# POST /complete - Chat completion
# POST /stream - Streaming completion
# POST /vision - Image analysis
# POST /generate_image - Image generation
# GET /models - List available models
# GET /providers - List available providers
```

**API Usage:**

```bash
# Chat completion
curl -X POST http://localhost:5000/complete \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "xai",
    "messages": [{"role": "user", "content": "Hello"}],
    "model": "grok-3",
    "temperature": 0.7
  }'

# Streaming
curl -X POST http://localhost:5000/stream \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "messages": [{"role": "user", "content": "Explain AI"}],
    "model": "gpt-4o"
  }'

# Vision
curl -X POST http://localhost:5000/vision \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "image_base64": "...",
    "prompt": "Describe this image"
  }'
```

### Universal Proxy

Generic proxy for any HTTP service:

```python
from web import create_universal_proxy_bp, create_proxy_app

# Create blueprint with routes
proxy_bp = create_universal_proxy_bp(
    routes={
        '/openai': 'https://api.openai.com',
        '/anthropic': 'https://api.anthropic.com'
    }
)

# Or full app
app = create_proxy_app(routes={
    '/external': 'https://api.example.com'
})

# Usage:
# GET /openai/v1/models -> proxied to https://api.openai.com/v1/models
# POST /anthropic/v1/complete -> proxied to https://api.anthropic.com/v1/complete
```

### Authentication

Bearer token and signed token authentication:

```python
from web import require_api_token, get_bearer_token, generate_signed_token, verify_signed_token
from flask import Flask, request, jsonify

app = Flask(__name__)

# Bearer token auth
@app.route('/protected')
@require_api_token(['valid-token-1', 'valid-token-2'])
def protected_endpoint():
    return jsonify({'message': 'Authenticated!'})

# Or manual token check
@app.route('/manual')
def manual_check():
    token = get_bearer_token(request)
    if token != 'valid-token':
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'message': 'OK'})

# Signed tokens (JWT-like)
secret_key = 'your-secret-key'

@app.route('/login')
def login():
    token = generate_signed_token(
        payload={'user_id': '123'},
        secret_key=secret_key,
        ttl=3600  # 1 hour
    )
    return jsonify({'token': token})

@app.route('/verify')
def verify():
    token = get_bearer_token(request)
    payload = verify_signed_token(token, secret_key)
    if payload:
        return jsonify({'user_id': payload['user_id']})
    return jsonify({'error': 'Invalid token'}), 401
```

### CORS Configuration

Enable cross-origin requests:

```python
from web import setup_cors
from flask import Flask

app = Flask(__name__)

# Basic CORS
setup_cors(app)

# Custom CORS
setup_cors(app, origins=['https://example.com'], methods=['GET', 'POST'])

# Or configure manually
from flask_cors import CORS
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://example.com"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

### Rate Limiting

API rate limiting middleware:

```python
from web import RateLimiter
from flask import Flask, jsonify

app = Flask(__name__)

# Create rate limiter
limiter = RateLimiter(
    calls=100,      # 100 requests
    period=60,      # per 60 seconds
    by_ip=True      # per IP address
)

@app.route('/api/endpoint')
def limited_endpoint():
    # Check rate limit
    if not limiter.check_limit(request.remote_addr):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    # Process request
    return jsonify({'message': 'OK'})

# Or use decorator pattern
@app.route('/api/other')
@limiter.limit(100, 60)  # 100 per minute
def other_endpoint():
    return jsonify({'message': 'OK'})
```

### Health Endpoints

Service health checks:

```python
from web import create_health_endpoint
from flask import Flask

app = Flask(__name__)

# Create /health endpoint
create_health_endpoint(app)

# Custom health check
def custom_health_check():
    # Check dependencies
    redis_ok = check_redis()
    db_ok = check_database()

    return {
        'status': 'healthy' if (redis_ok and db_ok) else 'unhealthy',
        'checks': {
            'redis': 'ok' if redis_ok else 'failed',
            'database': 'ok' if db_ok else 'failed'
        }
    }

create_health_endpoint(app, health_check_fn=custom_health_check)

# GET /health
# Response:
# {
#   "status": "healthy",
#   "timestamp": "2024-01-01T12:00:00Z",
#   "checks": {...}
# }
```

### Vision Service Utilities

Image processing helpers for vision endpoints:

```python
from web import (
    decode_image_from_request,
    validate_image_size,
    create_success_response,
    create_error_response
)
from flask import Flask, request

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze_image():
    try:
        # Decode image from request
        image_data = decode_image_from_request(request)

        # Validate size
        if not validate_image_size(image_data, max_size_mb=10):
            return create_error_response('Image too large', 400)

        # Process image
        result = process_image(image_data)

        return create_success_response(result)

    except Exception as e:
        return create_error_response(str(e), 500)
```

### Middleware

Request logging, error handling, and correlation IDs:

```python
from web import (
    register_request_logging,
    register_error_handlers,
    add_correlation_id
)
from flask import Flask

app = Flask(__name__)

# Add correlation ID to all requests
app.before_request(add_correlation_id)

# Log all requests
register_request_logging(app)

# Register error handlers
register_error_handlers(app)

# Custom error handler
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404
```

### Dreamwalker App

Web interface for orchestrator workflows:

```python
from web import create_dreamwalker_app

# Create Dreamwalker app
app = create_dreamwalker_app(
    port=5080,
    orchestrator_config={
        'providers': ['xai', 'anthropic'],
        'default_model': 'grok-3'
    }
)

# Run
if __name__ == '__main__':
    app.run(port=5080)

# Endpoints:
# GET / - Web interface
# POST /api/workflows - Create workflow
# GET /api/workflows/:id - Get workflow status
# POST /api/workflows/:id/cancel - Cancel workflow
# GET /stream/:id - SSE stream for workflow
```

### Creating Full API

```python
from flask import Flask, jsonify
from web import (
    create_llm_proxy_app,
    setup_cors,
    create_health_endpoint,
    register_request_logging,
    register_error_handlers,
    require_api_token
)

# Create app
app = create_llm_proxy_app()

# Configure CORS
setup_cors(app, origins=['https://app.example.com'])

# Add health check
create_health_endpoint(app)

# Add middleware
register_request_logging(app)
register_error_handlers(app)

# Add custom endpoint
@app.route('/api/custom')
@require_api_token(['valid-token'])
def custom_endpoint():
    return jsonify({'message': 'Custom endpoint'})

# Run
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Response Helpers

```python
from web import create_success_response, create_error_response, truncate_text

# Success response
return create_success_response(
    data={'result': 'value'},
    message='Operation successful',
    status_code=200
)
# Returns: {
#   'success': True,
#   'data': {'result': 'value'},
#   'message': 'Operation successful'
# }

# Error response
return create_error_response(
    message='Something went wrong',
    status_code=500,
    details={'error_code': 'E001'}
)
# Returns: {
#   'success': False,
#   'error': 'Something went wrong',
#   'details': {'error_code': 'E001'}
# }

# Truncate long text
short = truncate_text('Very long text...', max_length=100)
```

### Testing

```python
import pytest
from web import create_llm_proxy_app

@pytest.fixture
def client():
    app = create_llm_proxy_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

def test_llm_proxy(client):
    response = client.post('/complete', json={
        'provider': 'xai',
        'messages': [{'role': 'user', 'content': 'Test'}],
        'model': 'grok-3'
    })
    assert response.status_code == 200
```

### Files in This Module

- `llm_proxy_blueprint.py` - LLM proxy blueprint
- `universal_proxy.py` - Generic HTTP proxy
- `auth.py` - Authentication utilities
- `cors_config.py` - CORS configuration
- `rate_limit.py` - Rate limiting
- `health.py` - Health check endpoints
- `vision_service.py` - Image processing utilities
- `middleware.py` - Request logging, error handlers
- `dreamwalker/` - Dreamwalker web interface

### Dependencies

- `flask` - Web framework
- `flask-cors` - CORS support
- Optional: `redis` for distributed rate limiting

### Configuration

Via environment variables:

```bash
export FLASK_ENV=development
export API_TOKENS=token1,token2,token3
export CORS_ORIGINS=https://app.example.com
export RATE_LIMIT_CALLS=100
export RATE_LIMIT_PERIOD=60
```

### Best Practices

- Use blueprints for modular organization
- Enable CORS only for trusted origins
- Implement rate limiting on public endpoints
- Use authentication for sensitive endpoints
- Add health checks for monitoring
- Log all requests in production
- Use correlation IDs for request tracking
- Handle errors gracefully
- Validate input data
- Return consistent response formats

### Common Patterns

#### Multi-Provider API
```python
from web import create_llm_proxy_app
from llm_providers import ProviderFactory

app = create_llm_proxy_app(providers=[
    'openai', 'anthropic', 'xai', 'gemini'
])

# Clients can choose provider per request
# POST /complete {"provider": "xai", ...}
# POST /complete {"provider": "anthropic", ...}
```

#### Authenticated Proxy
```python
from web import create_proxy_app, require_api_token

app = create_proxy_app(routes={
    '/external': 'https://api.example.com'
})

# Add auth to all routes
for rule in app.url_map.iter_rules():
    view_func = app.view_functions[rule.endpoint]
    app.view_functions[rule.endpoint] = require_api_token(['token'])(view_func)
```

#### Rate-Limited API
```python
from web import RateLimiter
from flask import Flask, request, jsonify

app = Flask(__name__)
limiter = RateLimiter(calls=100, period=60)

@app.before_request
def check_rate_limit():
    if not limiter.check_limit(request.remote_addr):
        return jsonify({'error': 'Rate limit exceeded'}), 429
```

### Deployment

```bash
# Development
python app.py

# Production with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or with Caddy reverse proxy (already configured)
# Runs on port configured in service_manager
```

### Integration with Caddy

Services are proxied via Caddy:

```
# Caddyfile
d.reamwalk.com {
    reverse_proxy /llm-proxy/* localhost:5000
    reverse_proxy /dreamwalker/* localhost:5080
}
```

Access at:
- https://d.reamwalk.com/llm-proxy/complete
- https://d.reamwalk.com/dreamwalker/
