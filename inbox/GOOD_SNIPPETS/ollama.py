"""
Ollama provider for the Camina API v3.
Handles connections to the local Ollama server for LLM inference.
"""

import os
import json
import logging
import requests
import base64
from datetime import datetime
from typing import Dict, Generator, List, Optional, Any, Union

# Import base provider from providers snippet
from snippets.providers import BaseProvider

# Configure logging
logger = logging.getLogger(__name__)

# Try to import PIL for image processing
try:
    from PIL import Image
    import io
    has_pil = True
    logger.info("Successfully imported PIL.Image for image processing")
except ImportError:
    has_pil = False
    logger.warning("PIL not available. Image processing will be limited.")

class OllamaProvider(BaseProvider):
    """
    Provider implementation for Ollama API.
    Supports chat streaming, vision capabilities, and local model management.
    """
    def __init__(self, api_key: str = None):
        """
        Initialize the Ollama client with the host URL.
        Ollama doesn't require an API key, but we accept it for compatibility.
        
        Args:
            api_key: Not used for Ollama, but required by BaseProvider
        """
        # Initialize with default API key (not used by Ollama)
        super().__init__(api_key if api_key else "")
        
        # Determine Ollama host from environment or use default
        self.host = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
        logger.info(f"Initializing Ollama Provider with host: {self.host}")
        
        # Check if Ollama server is running
        try:
            response = requests.get(f"{self.host}", timeout=2)
            if response.ok:
                logger.info("Successfully connected to Ollama server")
            else:
                logger.warning(f"Ollama server responded with status {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Ollama server: {e}")
    
    def _check_server_status(self) -> bool:
        """
        Check if the Ollama server is running and accessible.
        
        Returns:
            bool: True if server is accessible, False otherwise
        """
        try:
            response = requests.get(f"{self.host}", timeout=2)
            return response.ok
        except requests.RequestException:
            return False
    
    def list_models(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get available Ollama models.
        
        Returns:
            List[Dict]: List of available models with their details
        """
        try:
            # Check if server is running
            if not self._check_server_status():
                logger.error("Ollama server is not accessible")
                return []
            
            # Get list of models
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if not response.ok:
                logger.error(f"Failed to fetch models: {response.text}")
                return []
            
            models_data = response.json().get('models', [])
            processed_models = []
            
            # Process each model
            for model in models_data:
                try:
                    # Get detailed model info
                    details_response = requests.post(
                        f"{self.host}/api/show",
                        json={"name": model['name']}
                    )
                    if not details_response.ok:
                        continue
                        
                    details = details_response.json()
                    model_details = details.get('details', {})
                    
                    # Determine capabilities based on families
                    capabilities = ["text"]  # All models support text
                    families = model_details.get('families', [])
                    if "clip" in families:
                        capabilities.append("vision")
                    
                    # Create enhanced model info
                    model_info = {
                        "id": model['name'],
                        "name": model['name'],
                        "description": f"Ollama {model_details.get('family', '').upper()} model - {model_details.get('parameter_size', 'Unknown')} parameters",
                        "capabilities": capabilities,
                        "created_at": model.get('modified_at', datetime.now().isoformat()),
                        "provider": "ollama"
                    }
                    processed_models.append(model_info)
                except Exception as e:
                    logger.error(f"Error processing model {model['name']}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(processed_models)} models from Ollama")
            return processed_models
            
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return []
    
    def encode_image(self, image_path: str) -> Optional[str]:
        """
        Encode an image file to base64 for multimodal prompts.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Optional[str]: Base64 encoded image data or None if encoding fails
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_data = base64.b64encode(image_file.read()).decode('utf-8')
                logger.info(f"Successfully encoded image from path: {image_path}")
                return encoded_data
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            return None
    
    def process_image(self, image_path: str) -> Optional[str]:
        """
        Process an image for use in multimodal requests.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Optional[str]: Encoded image data or None if processing failed
        """
        if not has_pil:
            logger.warning("PIL not available, using basic encoding")
            return self.encode_image(image_path)
            
        try:
            logger.info(f"Processing image from path: {image_path}")
            
            # Check if the file exists
            if not os.path.exists(image_path):
                logger.error(f"File does not exist: {image_path}")
                return None
                
            # Open the image and convert if needed
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                # Resize if too large
                if img.size[0] > 1024 or img.size[1] > 1024:
                    ratio = min(1024/img.size[0], 1024/img.size[1])
                    new_size = (int(img.size[0]*ratio), int(img.size[1]*ratio))
                    img = img.resize(new_size, Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)
                
                # Save to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                
                # Encode to base64
                encoded_data = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                logger.info(f"Successfully processed image, length={len(encoded_data)}")
                return encoded_data
                
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            # Fall back to basic encoding
            return self.encode_image(image_path)
    
    def chat_completion(self, prompt: str, model: str = "llama2", **kwargs) -> Dict[str, Any]:
        """
        Get a chat completion from Ollama.
        
        Args:
            prompt: The user's message
            model: The Ollama model to use
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Response containing the completion
        """
        try:
            # Check if server is running
            if not self._check_server_status():
                return {"error": "Ollama server is not accessible", "content": ""}
            
            # Process image if provided
            image_data = None
            image_path = kwargs.get('image_path')
            if image_path:
                image_data = self.process_image(image_path)
            
            # Get optional parameters
            temperature = float(kwargs.get('temperature', 0.7))
            
            # Build request data
            data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": kwargs.get('max_tokens', -1)  # -1 lets model decide
                }
            }
            
            # Add images if provided
            if image_data:
                logger.info(f"Adding image data to request")
                data["images"] = [image_data]
            
            # Handle messages if provided in chat format
            messages = kwargs.get('messages')
            if messages:
                # Handle messages in proper format
                # This will be implemented in a future version when Ollama supports the messages format
                # For now, we'll construct a prompt from the messages
                if isinstance(messages, list) and len(messages) > 0:
                    full_prompt = ""
                    for msg in messages:
                        role = msg.get('role', 'user')
                        content = msg.get('content', '')
                        full_prompt += f"{role.upper()}: {content}\n"
                    
                    # Replace the original prompt
                    data["prompt"] = full_prompt + f"ASSISTANT: "
            
            # Make request
            logger.info(f"Sending completion request to Ollama API with model: {model}")
            response = requests.post(f"{self.host}/api/generate", json=data, timeout=60)
            
            if not response.ok:
                logger.error(f"Ollama API request failed: {response.text}")
                return {
                    "error": f"Ollama API error: {response.status_code}",
                    "content": "",
                    "model": model,
                    "provider": "ollama"
                }
            
            # Parse response
            result = response.json()
            
            return {
                "model": model,
                "content": result.get("response", ""),
                "provider": "ollama",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in chat_completion: {e}")
            return {
                "error": str(e),
                "content": f"Error: {str(e)}",
                "model": model,
                "provider": "ollama"
            }
    
    def stream_chat_completion(
        self,
        prompt: str,
        model: str = "llama2",
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream a chat completion from Ollama.
        
        Args:
            prompt: The user's message
            model: The Ollama model to use
            **kwargs: Additional parameters
            
        Yields:
            str: Chunks of the response text as they arrive
        """
        try:
            # Check if server is running
            if not self._check_server_status():
                yield "Error: Ollama server is not accessible"
                return
            
            # Process image if provided
            image_data = None
            image_path = kwargs.get('image_path')
            if image_path:
                logger.info(f"Processing image from path: {image_path}")
                image_data = self.process_image(image_path)
                if not image_data:
                    logger.error(f"Failed to process image from path: {image_path}")
            
            # Get optional parameters
            temperature = float(kwargs.get('temperature', 0.7))
            
            # Prepare the request data
            data = {
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": kwargs.get('max_tokens', -1)  # -1 to let model decide
                }
            }
            
            # Add image if provided
            if image_data:
                logger.info(f"Adding image data to request")
                data["images"] = [image_data]
            
            # Make streaming request
            logger.info(f"Sending streaming request to Ollama API with model: {model}")
            response = requests.post(
                f"{self.host}/api/generate",
                json=data,
                stream=True,
                timeout=60
            )
            
            if not response.ok:
                error_msg = f"Ollama API request failed: {response.text}"
                logger.error(error_msg)
                yield f"Error: {error_msg}"
                return
            
            # Process streaming response
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if chunk.get("response"):
                            yield chunk["response"]
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error in stream_chat_completion: {e}")
            yield f"Error: {str(e)}"
    
    def call_tool(self, prompt: str, model: str, tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Use the model to call tools based on the prompt.
        
        Args:
            prompt: The user's message
            model: The model to use
            tools: List of tool definitions
            **kwargs: Additional parameters
            
        Returns:
            Dict containing the response and any tool calls
        """
        try:
            # Check if server is running
            if not self._check_server_status():
                return {"error": "Ollama server is not accessible", "content": ""}
            
            # Ollama doesn't have native tool calling, so we'll format the tools as part of the prompt
            tools_str = json.dumps(tools, indent=2)
            enhanced_prompt = f"{prompt}\n\nAvailable tools:\n{tools_str}\n\nPlease use these tools to help the user. Respond in JSON format with a 'tool_calls' array. Each tool call should include a 'name' and 'arguments' object."
            
            # Stream the response - will collect all chunks for a complete response
            full_response = ""
            for chunk in self.stream_chat_completion(
                enhanced_prompt, 
                model=model,
                max_tokens=kwargs.get('max_tokens', -1)
            ):
                full_response += chunk
                
            # Try to extract JSON from the response
            try:
                # Look for JSON-like structure in the response
                import re
                json_match = re.search(r'\{.*\}', full_response, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                    tool_data = json.loads(json_text)
                    
                    # If tool_calls is present, return it
                    if 'tool_calls' in tool_data:
                        return {
                            "content": full_response,
                            "tool_calls": tool_data['tool_calls'],
                            "model": model,
                            "provider": "ollama"
                        }
            except:
                pass
                
            # Return the raw response if no tool calls found
            return {
                "content": full_response,
                "tool_calls": [],
                "model": model,
                "provider": "ollama"
            }
            
        except Exception as e:
            logger.error(f"Error calling tools: {e}")
            return {
                "error": str(e),
                "content": f"Error calling tools: {str(e)}",
                "tool_calls": [],
                "model": model,
                "provider": "ollama"
            }
            
    def sample_request(self) -> Dict[str, Any]:
        """
        Make a simple request to test the Ollama API connection.
        
        Returns:
            Dict with status information
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.ok:
                return {
                    "status": "ok",
                    "message": "Successfully connected to Ollama API",
                    "models_count": len(response.json().get('models', [])),
                    "provider": "ollama"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Ollama API error: {response.status_code}",
                    "provider": "ollama"
                }
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Failed to connect to Ollama API: {str(e)}",
                "provider": "ollama"
            } 