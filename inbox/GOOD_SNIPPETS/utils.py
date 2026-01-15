"""
Utility functions for the Camina API v3.
Contains helper functions for common tasks across the API.
"""

import base64
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional, Union
import mimetypes
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Initialize mimetypes
mimetypes.init()


def get_mime_type(file_path: str) -> str:
    """
    Get the MIME type of a file.
    
    Args:
        file_path: Path to the file
    
    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        # Default to application/octet-stream if type cannot be determined
        return 'application/octet-stream'
    return mime_type


def encode_file_to_base64(file_path: str) -> Optional[str]:
    """
    Encode a file to base64.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Base64 encoded file or None if encoding failed
    """
    try:
        with open(file_path, 'rb') as file:
            file_data = file.read()
            encoded_data = base64.b64encode(file_data).decode('utf-8')
            return encoded_data
    except Exception as e:
        logger.error(f"Error encoding file to base64: {str(e)}")
        return None


def format_timestamp(timestamp: Union[int, float, str]) -> str:
    """
    Format a timestamp to ISO 8601 format.
    
    Args:
        timestamp: Unix timestamp (int/float) or datetime string
    
    Returns:
        Formatted timestamp string
    """
    try:
        # Handle numeric timestamp
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
            return dt.isoformat()
        
        # Handle string timestamp
        if isinstance(timestamp, str):
            # Check if it's already ISO format
            if 'T' in timestamp and ('+' in timestamp or 'Z' in timestamp):
                return timestamp
            
            # Try parsing as datetime
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(timestamp, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
        
        # Default - return current time if parsing fails
        return datetime.now().isoformat()
    except Exception as e:
        logger.error(f"Error formatting timestamp: {str(e)}")
        return datetime.now().isoformat()


def generate_error_response(message: str, status_code: int = 500) -> Dict[str, Any]:
    """
    Generate a standardized error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
    
    Returns:
        Error response dictionary
    """
    return {
        "error": {
            "message": message,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat()
        }
    }


def parse_json_safely(json_str: str) -> Dict[str, Any]:
    """
    Parse JSON string safely, handling errors.
    
    Args:
        json_str: JSON string to parse
    
    Returns:
        Parsed JSON object or empty dict if parsing failed
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        return {}


def validate_api_key(api_key: str, required_prefix: str = 'key-') -> bool:
    """
    Validate API key format.
    
    Args:
        api_key: API key to validate
        required_prefix: Expected prefix for the API key
    
    Returns:
        True if valid, False otherwise
    """
    if not api_key:
        return False
    
    if not api_key.startswith(required_prefix):
        return False
    
    # Check minimum length
    if len(api_key) < 20:
        return False
    
    return True


def measure_execution_time(func):
    """
    Decorator to measure execution time of a function.
    
    Args:
        func: Function to measure
    
    Returns:
        Wrapped function that logs execution time
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    
    return wrapper 