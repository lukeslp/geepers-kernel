"""
Common patterns for vision-based Flask services.
Handles image decoding, provider selection, and response formatting.

This module eliminates duplicate image handling code across vision services
like alttext, accessibility-checker, and illustrator.

Usage:
    from shared.web.vision_service import decode_image_from_request, create_success_response, create_error_response

    @app.route('/analyze', methods=['POST'])
    def analyze():
        try:
            img_bytes, data = decode_image_from_request()
            provider_name = data.get('provider', 'xai')

            provider = ProviderFactory.get_provider(provider_name)
            result = provider.analyze_image(img_bytes, "Analyze this image")

            return create_success_response({
                'analysis': result.content,
                'provider': provider_name
            })

        except Exception as e:
            return create_error_response(e)
"""

import base64
from typing import Union, Dict, Any, Tuple
from flask import request, jsonify


def decode_image_from_request() -> Tuple[bytes, Dict[str, Any]]:
    """
    Decode image from either JSON (base64) or multipart/form-data.

    This function handles both common ways clients send images:
    1. JSON with base64-encoded image string
    2. Multipart form data with file upload

    Returns:
        Tuple of (image_bytes, request_data_dict)

    Raises:
        ValueError: If no image is provided or format is invalid

    Example:
        img_bytes, data = decode_image_from_request()
        provider_name = data.get('provider', 'xai')
    """
    # Handle JSON request with base64-encoded image
    if request.is_json:
        data = request.get_json()

        if 'image' not in data:
            raise ValueError('Missing image data in JSON request')

        # Decode base64
        image_data = data['image']

        # Remove data URI prefix if present (e.g., "data:image/png;base64,...")
        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]

        try:
            img_bytes = base64.b64decode(image_data)
        except Exception as e:
            raise ValueError(f'Invalid base64 image data: {e}')

        return img_bytes, data

    # Handle multipart/form-data (file upload)
    elif 'image' in request.files:
        img_bytes = request.files['image'].read()
        data = request.form.to_dict()
        return img_bytes, data

    else:
        raise ValueError('No image provided. Send either JSON with "image" field or multipart/form-data with "image" file.')


def create_success_response(data: Dict[str, Any], status_code: int = 200):
    """
    Create a standardized success response.

    Args:
        data: Dictionary of response data to include
        status_code: HTTP status code (default: 200)

    Returns:
        Flask response tuple (json, status_code)

    Example:
        return create_success_response({
            'alt_text': 'A beautiful sunset',
            'provider': 'xai',
            'tokens_used': 150
        })
    """
    return jsonify({
        'success': True,
        **data
    }), status_code


def create_error_response(error: Union[str, Exception], status_code: int = 500):
    """
    Create a standardized error response.

    Args:
        error: Error message or exception
        status_code: HTTP status code (default: 500)

    Returns:
        Flask response tuple (json, status_code)

    Example:
        return create_error_response('Image too large', 400)
        return create_error_response(ValueError('Invalid format'), 400)
    """
    return jsonify({
        'success': False,
        'error': str(error)
    }), status_code


def truncate_text(text: str, max_length: int, prefer_sentence: bool = True) -> str:
    """
    Truncate text to maximum length, preferring sentence boundaries.

    Args:
        text: Text to truncate
        max_length: Maximum length in characters
        prefer_sentence: Try to truncate at sentence boundary if True

    Returns:
        Truncated text

    Example:
        alt_text = truncate_text(long_description, 125, prefer_sentence=True)
    """
    if len(text) <= max_length:
        return text

    if prefer_sentence and '. ' in text[:max_length]:
        # Truncate at last sentence boundary before max_length
        truncated = text[:text[:max_length].rfind('. ') + 1]
        return truncated
    else:
        # Hard truncate with ellipsis
        return text[:max_length - 3] + '...'


def validate_image_size(img_bytes: bytes, max_size_mb: int = 10) -> None:
    """
    Validate image size doesn't exceed limit.

    Args:
        img_bytes: Raw image bytes
        max_size_mb: Maximum size in megabytes

    Raises:
        ValueError: If image exceeds size limit

    Example:
        validate_image_size(img_bytes, max_size_mb=5)
    """
    size_mb = len(img_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(f'Image too large: {size_mb:.1f}MB (max: {max_size_mb}MB)')
