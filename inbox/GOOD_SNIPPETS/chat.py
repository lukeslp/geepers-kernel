"""
Chat endpoints for the API v3.
Handles chat completions and streaming with various providers including Ollama.
"""

import os
import json
import logging
import time
import base64
from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_cors import cross_origin
from typing import Dict, Any, List, Optional, Generator, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create blueprint
chat_bp = Blueprint('chat', __name__)

# Import provider system
from snippets.providers import ProviderFactory

@chat_bp.route('/completions', methods=['POST'])
@cross_origin()
def chat_completions():
    """
    Handle chat completion requests with various providers.
    
    Request body should include:
    - provider: string, provider name (e.g., 'ollama', 'openai')
    - model: string, model name
    - messages: array of message objects (role, content)
    - stream: boolean, optional, whether to stream the response
    - tools: array of tool objects, optional
    - image: base64 encoded image, optional
    """
    try:
        data = request.json
        
        # Validate request
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        provider_name = data.get('provider')
        if not provider_name:
            return jsonify({"error": "Provider is required"}), 400
        
        model = data.get('model')
        if not model:
            return jsonify({"error": "Model is required"}), 400
        
        messages = data.get('messages', [])
        if not messages:
            return jsonify({"error": "Messages are required"}), 400
        
        # Optional parameters
        stream = data.get('stream', False)
        tools = data.get('tools', [])
        image_data = data.get('image')
        
        # Get provider
        provider = ProviderFactory.get_provider(provider_name)
        if not provider:
            return jsonify({"error": f"Provider '{provider_name}' not found"}), 404
        
        # Process image if provided
        image_obj = None
        if image_data:
            try:
                image_obj = provider.process_image(image_data)
                logger.info(f"Processed image for {provider_name}")
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                return jsonify({"error": f"Error processing image: {str(e)}"}), 400
        
        # Handle streaming response
        if stream:
            def generate():
                try:
                    for chunk in provider.stream_chat_completion(
                        model=model, 
                        messages=messages,
                        tools=tools,
                        image=image_obj
                    ):
                        yield f"data: {json.dumps(chunk)}\n\n"
                except Exception as e:
                    logger.error(f"Error in streaming response: {str(e)}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                yield "data: [DONE]\n\n"
            
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream'
            )
        
        # Handle non-streaming response
        try:
            # If tools are provided, use the tool calling feature
            if tools:
                response = provider.call_tool(
                    model=model,
                    messages=messages,
                    tools=tools,
                    image=image_obj
                )
            else:
                response = provider.chat_completion(
                    model=model,
                    messages=messages,
                    image=image_obj
                )
            
            return jsonify(response)
        
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            return jsonify({"error": str(e)}), 500
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/providers', methods=['GET'])
@cross_origin()
def list_chat_providers():
    """List available chat providers and their models."""
    providers_with_models = {}
    available_providers = ProviderFactory.get_available_providers()
    
    for provider_name, available in available_providers.items():
        if available:
            provider = ProviderFactory.get_provider(provider_name)
            if provider:
                try:
                    models = provider.list_models()
                    providers_with_models[provider_name] = {
                        "available": True,
                        "models": models
                    }
                except Exception as e:
                    providers_with_models[provider_name] = {
                        "available": True,
                        "error": str(e),
                        "models": []
                    }
            else:
                providers_with_models[provider_name] = {
                    "available": False,
                    "error": "Provider instance not found",
                    "models": []
                }
        else:
            providers_with_models[provider_name] = {
                "available": False,
                "models": []
            }
    
    return jsonify({
        "providers": providers_with_models
    })

@chat_bp.route('/models', methods=['GET'])
@cross_origin()
def list_models():
    """
    List available models from all providers or a specific provider.
    
    Query parameters:
    - provider: The provider to list models from (optional)
    
    Returns:
        JSON object with the available models
    """
    try:
        # Get provider from query parameter
        provider_name = request.args.get('provider')
        
        # If provider is specified, return models from that provider
        if provider_name:
            provider = ProviderFactory.get_provider(provider_name)
            if not provider:
                return jsonify({"error": f"Provider '{provider_name}' not available"}), 400
                
            models = provider.list_models()
            return jsonify({
                "provider": provider_name,
                "models": models
            })
        
        # If no provider specified, return models from all available providers
        all_models = {}
        for provider_name, available in ProviderFactory.get_available_providers().items():
            if available:
                provider = ProviderFactory.get_provider(provider_name)
                if provider:
                    all_models[provider_name] = provider.list_models()
        
        return jsonify({
            "providers": list(all_models.keys()),
            "models": all_models
        })
    
    except Exception as e:
        logging.error(f"Error listing models: {str(e)}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/tools', methods=['POST'])
@cross_origin()
def call_tool():
    """
    Call a tool/function using an LLM provider.
    
    This endpoint processes a tool calling request and returns the result.
    
    Request JSON body:
    - provider: The provider to use (e.g., 'openai', 'anthropic', 'mistral')
    - model: The model to use
    - prompt: The user's message
    - tools: Array of tool schemas to make available
    - tool_choice: 'auto', 'required', or specific tool name
    
    Returns:
        JSON object with the tool call result
    """
    try:
        # Parse request data
        data = request.get_json() or {}
        
        # Get required parameters
        provider_name = data.get('provider', 'openai')
        model = data.get('model', 'gpt-3.5-turbo')
        prompt = data.get('prompt', '')
        tools = data.get('tools', [])
        
        # Validate required parameters
        if not prompt:
            return jsonify({"error": "Prompt parameter is required"}), 400
        
        if not tools or not isinstance(tools, list):
            return jsonify({"error": "Tools parameter must be a non-empty array"}), 400
        
        # Get provider instance
        provider = ProviderFactory.get_provider(provider_name)
        if not provider:
            return jsonify({"error": f"Provider '{provider_name}' not available"}), 400
        
        # Get optional parameters
        temperature = float(data.get('temperature', 0.7))
        max_tokens = int(data.get('max_tokens', 1024))
        tool_choice = data.get('tool_choice', 'auto')
        
        # Call the tool
        result = provider.call_tool(
            prompt=prompt,
            model=model,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            tool_choice=tool_choice
        )
        
        return jsonify(result)
    
    except Exception as e:
        logging.error(f"Error calling tool: {str(e)}")
        return jsonify({"error": str(e)}), 500 