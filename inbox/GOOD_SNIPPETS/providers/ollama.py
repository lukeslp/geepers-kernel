"""
Ollama Provider for the API v3
Handles interactions with Ollama for chat completions, image understanding, 
and model management.
"""

import os
import sys
import json
import logging
import requests
import time
from typing import Dict, List, Any, Optional, Generator, Union
from io import BytesIO
import base64
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaProvider:
    """Provider for Ollama API"""
    
    def __init__(self, host=None):
        """
        Initialize the Ollama provider.
        
        Args:
            host (str, optional): Ollama host URL. Defaults to http://localhost:11434.
        """
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.available = False
        self.models = []
        self.name = "ollama"
        self.version = "1.0.0"
        
        # Check if Ollama is available
        self.available = self._check_availability()
        if self.available:
            self.models = self._get_models()
            logger.info(f"Ollama provider initialized with host: {self.host}")
            logger.info(f"Available models: {', '.join([m['id'] for m in self.models])}")
        else:
            logger.warning(f"Ollama provider not available at {self.host}")
    
    def _check_availability(self) -> bool:
        """Check if Ollama server is available."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {str(e)}")
            return False
    
    def _get_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available models from Ollama.
        
        Returns:
            List of model dictionaries with 'id' and 'metadata'
        """
        models = []
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                for model in data.get("models", []):
                    model_info = {
                        "id": model["name"],
                        "metadata": {
                            "size": model.get("size", 0),
                            "modified_at": model.get("modified_at", ""),
                            "digest": model.get("digest", ""),
                            "details": self._get_model_details(model["name"])
                        }
                    }
                    models.append(model_info)
            return models
        except Exception as e:
            logger.error(f"Error fetching models from Ollama: {str(e)}")
            return []
    
    def _get_model_details(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific model."""
        try:
            response = requests.post(
                f"{self.host}/api/show",
                json={"name": model_name},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Error fetching model details: {str(e)}")
            return {}
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models from Ollama.
        
        Returns:
            List of model information dictionaries.
        """
        if not self.available:
            self.available = self._check_availability()
            if self.available:
                self.models = self._get_models()
        
        return self.models
    
    def process_image(self, image_data: str) -> Dict[str, Any]:
        """
        Process an image for multimodal models.
        
        Args:
            image_data (str): Base64 encoded image data with format prefix
                             (e.g., "data:image/jpeg;base64,...")
        
        Returns:
            Dict with image data formatted for Ollama
        """
        try:
            # Remove prefix if present
            if ";" in image_data and "," in image_data:
                image_data = image_data.split(",", 1)[1]
            
            # Decode base64 data
            image_bytes = base64.b64decode(image_data)
            
            # Ollama format for images
            return {
                "data": image_data,
                "format": "base64"
            }
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise ValueError(f"Invalid image data: {str(e)}")
    
    def chat_completion(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        image: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Generate a chat completion using Ollama.
        
        Args:
            model (str): Model name to use
            messages (List[Dict]): List of message dictionaries with 'role' and 'content'
            image (Dict, optional): Processed image for multimodal models
            temperature (float, optional): Controls randomness, default 0.7
            max_tokens (int, optional): Maximum tokens to generate, default 4096
        
        Returns:
            Response dictionary with completion text
        """
        if not self.available:
            raise ValueError("Ollama provider is not available")
        
        # Format messages for Ollama's API
        formatted_messages = []
        system_message = ""
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_message = content
            else:
                formatted_messages.append({
                    "role": "assistant" if role == "assistant" else "user",
                    "content": content
                })
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": formatted_messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # Add system message if provided
        if system_message:
            payload["system"] = system_message
        
        # Add image if provided
        if image and "data" in image:
            # Check if this is a vision model
            if not self._is_vision_model(model):
                logger.warning(f"Model {model} may not support images. Trying anyway.")
            
            # For Ollama multimodal models, add image to the last user message
            for i in range(len(payload["messages"])-1, -1, -1):
                if payload["messages"][i]["role"] == "user":
                    if isinstance(payload["messages"][i]["content"], str):
                        payload["messages"][i]["content"] = [
                            {"type": "text", "text": payload["messages"][i]["content"]},
                            {"type": "image", "image": image["data"]}
                        ]
                    break
        
        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.text}")
                return {"error": f"Ollama API error: {response.text}"}
            
            result = response.json()
            
            # Format response to match the expected structure
            return {
                "id": f"ollama-{model}-{result.get('created_at', '')}",
                "object": "chat.completion",
                "created": result.get("created_at", 0),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result.get("message", {}).get("content", "")
                        },
                        "finish_reason": result.get("done", True) and "stop" or "length"
                    }
                ],
                "usage": {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                }
            }
            
        except requests.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise ValueError(f"Ollama request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise ValueError(f"Chat completion error: {str(e)}")
    
    def stream_chat_completion(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]] = None,
        image: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream a chat completion using Ollama.
        
        Args:
            model (str): Model name to use
            messages (List[Dict]): List of message dictionaries with 'role' and 'content'
            tools (List[Dict], optional): Tool specifications for function calling
            image (Dict, optional): Processed image for multimodal models
            temperature (float, optional): Controls randomness, default 0.7
            max_tokens (int, optional): Maximum tokens to generate, default 4096
        
        Yields:
            Dict: Stream chunks in standard completion format
        """
        if not self.available:
            raise ValueError("Ollama provider is not available")
        
        # Format messages for Ollama's API
        formatted_messages = []
        system_message = ""
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_message = content
            else:
                formatted_messages.append({
                    "role": "assistant" if role == "assistant" else "user",
                    "content": content
                })
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": formatted_messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            },
            "stream": True
        }
        
        # Add system message if provided
        if system_message:
            payload["system"] = system_message
        
        # Add image if provided (same as in chat_completion method)
        if image and "data" in image:
            if not self._is_vision_model(model):
                logger.warning(f"Model {model} may not support images. Trying anyway.")
            
            for i in range(len(payload["messages"])-1, -1, -1):
                if payload["messages"][i]["role"] == "user":
                    if isinstance(payload["messages"][i]["content"], str):
                        payload["messages"][i]["content"] = [
                            {"type": "text", "text": payload["messages"][i]["content"]},
                            {"type": "image", "image": image["data"]}
                        ]
                    break
        
        try:
            response_id = f"ollama-{model}-{int(time.time())}"
            content_buffer = ""
            
            with requests.post(
                f"{self.host}/api/chat",
                json=payload,
                stream=True,
                timeout=60
            ) as response:
                if response.status_code != 200:
                    yield {
                        "error": f"Ollama API error: {response.text}",
                        "status_code": response.status_code
                    }
                    return
                
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    try:
                        chunk = json.loads(line)
                        
                        # Extract content from the chunk
                        new_content = chunk.get("message", {}).get("content", "")
                        if new_content:
                            content_buffer += new_content
                            
                            # Format response to match the expected structure
                            yield {
                                "id": response_id,
                                "object": "chat.completion.chunk",
                                "created": chunk.get("created_at", 0),
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {
                                            "role": "assistant",
                                            "content": new_content
                                        },
                                        "finish_reason": None
                                    }
                                ]
                            }
                        
                        # Final chunk
                        if chunk.get("done", False):
                            yield {
                                "id": response_id,
                                "object": "chat.completion.chunk",
                                "created": chunk.get("created_at", 0),
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {},
                                        "finish_reason": "stop"
                                    }
                                ]
                            }
                    
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in stream: {line}")
                    except Exception as e:
                        logger.error(f"Error processing stream chunk: {str(e)}")
                        yield {"error": str(e)}
        
        except requests.RequestException as e:
            logger.error(f"Stream request error: {str(e)}")
            yield {"error": f"Ollama stream request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in stream chat completion: {str(e)}")
            yield {"error": f"Stream completion error: {str(e)}"}
    
    def call_tool(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]],
        image: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Call a tool using an Ollama model. Note that this is a simplified implementation
        since Ollama doesn't have native function calling, we'll pass the tools as part of
        the system prompt.
        
        Args:
            model (str): Model name to use
            messages (List[Dict]): List of message objects
            tools (List[Dict]): Tool specifications
            image (Dict, optional): Processed image for multimodal models
            temperature (float, optional): Controls randomness
            max_tokens (int, optional): Maximum tokens to generate
        
        Returns:
            Dict: Response with tool calls if applicable
        """
        if not self.available:
            raise ValueError("Ollama provider is not available")
        
        # Create a system prompt explaining the function calling format
        tool_descriptions = "\n".join([
            f"- {tool['name']}: {tool.get('description', 'No description')}" 
            for tool in tools
        ])
        
        tool_parameters = {}
        for tool in tools:
            if "parameters" in tool:
                param_desc = []
                if "properties" in tool["parameters"]:
                    for param_name, param_info in tool["parameters"]["properties"].items():
                        param_desc.append(f"  - {param_name}: {param_info.get('description', 'No description')}")
                
                tool_parameters[tool["name"]] = "\n".join(param_desc)
        
        system_prompt = f"""You are an AI assistant that can use tools.
Available tools:
{tool_descriptions}

Tool parameters:
{json.dumps(tool_parameters, indent=2)}

To use a tool, your response must be formatted as a JSON object with a "tool_calls" array, like this:
{{
  "tool_calls": [
    {{
      "name": "tool_name",
      "parameters": {{
        "param1": "value1",
        "param2": "value2"
      }}
    }}
  ]
}}

Think carefully about whether you need to use a tool based on the user's request.
If you don't need to use a tool, just respond normally.
When using a tool, make sure to provide all required parameters.
"""
        
        # Add system message to beginning of messages
        messages_with_system = [{"role": "system", "content": system_prompt}] + messages
        
        # Get completion from model
        response = self.chat_completion(
            model=model,
            messages=messages_with_system,
            image=image,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Parse response for tool calls
        assistant_message = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Check if the response contains a JSON object with tool_calls
        try:
            # Extract JSON from the response if it's wrapped in markdown code blocks
            if "```json" in assistant_message and "```" in assistant_message.split("```json", 1)[1]:
                json_str = assistant_message.split("```json", 1)[1].split("```", 1)[0].strip()
                tool_data = json.loads(json_str)
            elif "```" in assistant_message and "```" in assistant_message.split("```", 1)[1]:
                json_str = assistant_message.split("```", 1)[1].split("```", 1)[0].strip()
                tool_data = json.loads(json_str)
            else:
                # Try to parse the whole message as JSON
                tool_data = json.loads(assistant_message)
            
            if "tool_calls" in tool_data:
                # Format response to include tool calls
                tool_calls = []
                for i, tool_call in enumerate(tool_data["tool_calls"]):
                    tool_calls.append({
                        "id": f"call_{model}_{i}",
                        "type": "function",
                        "function": {
                            "name": tool_call["name"],
                            "arguments": json.dumps(tool_call["parameters"])
                        }
                    })
                
                # Return formatted response with tool calls
                return {
                    "id": response.get("id", f"ollama-{model}-tool"),
                    "object": "chat.completion",
                    "created": response.get("created", 0),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": tool_calls
                            },
                            "finish_reason": "tool_calls"
                        }
                    ],
                    "usage": response.get("usage", {})
                }
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse tool call: {str(e)}")
        
        # Return original response if no valid tool call format was found
        return response
    
    def _is_vision_model(self, model: str) -> bool:
        """
        Check if the model supports multimodal inputs.
        This is an approximation as Ollama doesn't provide this information directly.
        
        Args:
            model (str): Model name to check
            
        Returns:
            bool: True if model likely supports vision, False otherwise
        """
        # Common vision model indicators
        vision_indicators = ["vision", "llava", "bakllava", "clip", 
                            "image", "multi-modal", "multimodal"]
        
        # Check model ID for vision indicators
        model_lower = model.lower()
        return any(indicator in model_lower for indicator in vision_indicators)
    
    def status(self) -> Dict[str, Any]:
        """
        Get status of the Ollama provider.
        
        Returns:
            Dict with provider status information
        """
        return {
            "name": self.name,
            "version": self.version,
            "available": self.available,
            "host": self.host,
            "model_count": len(self.models),
            "models": [m["id"] for m in self.models]
        } 