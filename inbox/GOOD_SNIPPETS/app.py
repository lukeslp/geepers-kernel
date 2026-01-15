"""
Sample Flask application integrating all the API snippets.
This serves as a basic example of how to set up the v3 API.
"""

import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize application
app = Flask(__name__)
CORS(app)

# Set default config values
app.config.update(
    PORT=int(os.environ.get('PORT', 8435)),
    DEBUG=os.environ.get('DEBUG', 'true').lower() == 'true',
    LOG_LEVEL=os.environ.get('LOG_LEVEL', 'INFO'),
    API_VERSION='v3',
    OLLAMA_HOST=os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
)

# Import provider system
from snippets.providers import ProviderFactory, BaseProvider
from snippets.ollama import OllamaProvider

# Register Ollama provider
ProviderFactory.register_provider('ollama', OllamaProvider)

# Initialize Ollama provider
ollama_provider = ProviderFactory.get_provider('ollama')
if ollama_provider:
    logger.info("Successfully initialized Ollama provider")
    # Test connection to Ollama
    status = ollama_provider.sample_request()
    if status['status'] == 'ok':
        logger.info(f"Ollama connection successful: {status['models_count']} models available")
    else:
        logger.warning(f"Ollama connection issue: {status['message']}")
else:
    logger.warning("Failed to initialize Ollama provider")

# Import and register blueprints
from snippets.research import research_bp
from snippets.tools import tools_bp
from snippets.chat import chat_bp

# Register blueprints with API version prefix
API_PREFIX = f"/api/{app.config['API_VERSION']}"
app.register_blueprint(research_bp, url_prefix=f"{API_PREFIX}/research")
app.register_blueprint(tools_bp, url_prefix=f"{API_PREFIX}/tools")
app.register_blueprint(chat_bp, url_prefix=f"{API_PREFIX}/chat")

@app.route('/')
def index():
    """Root endpoint providing API information."""
    return jsonify({
        "name": "Camina API",
        "version": app.config['API_VERSION'],
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "chat": f"{API_PREFIX}/chat",
            "research": f"{API_PREFIX}/research",
            "tools": f"{API_PREFIX}/tools"
        }
    })

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "version": app.config['API_VERSION'],
        "providers": {
            "ollama": ollama_provider._check_server_status() if ollama_provider else False
        }
    })

@app.route('/providers')
def list_providers():
    """List available providers and their status."""
    providers_status = ProviderFactory.get_available_providers()
    
    # Check Ollama specifically
    if 'ollama' in providers_status and providers_status['ollama']:
        if ollama_provider:
            status = ollama_provider.sample_request()
            providers_status['ollama_details'] = status
    
    return jsonify({
        "providers": providers_status
    })

@app.route('/ollama/models')
def list_ollama_models():
    """List available Ollama models."""
    if not ollama_provider:
        return jsonify({"error": "Ollama provider not available"}), 400
    
    models = ollama_provider.list_models()
    return jsonify({
        "models": models,
        "count": len(models)
    })

@app.route('/docs')
def documentation():
    """API documentation endpoint."""
    return jsonify({
        "message": "Documentation coming soon",
        "swagger_ui": "/swagger-ui",
        "ollama_status": ollama_provider.sample_request() if ollama_provider else {"status": "provider_unavailable"}
    })

if __name__ == "__main__":
    port = app.config['PORT']
    debug = app.config['DEBUG']
    
    logger.info(f"Starting Camina API v3 on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Ollama host: {app.config['OLLAMA_HOST']}")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 