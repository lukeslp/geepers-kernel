"""
Common utilities for configuration and error handling.
"""

import os
from typing import Any
import logging

# Import file utilities for easy access

# Import progress tracking utilities

# Import TTS utilities

# Import execution safety utilities

# Import citation utilities

# Import vision utilities

# Import time utilities

# Import multi-search utilities

# Import document parsing utilities

# Import embedding utilities

# Text processing helpers

# Data validation helpers

# Retry helpers

# Rate limiter helpers

# Crypto helpers

# Format converter
from .format_converter import (
    FormatConverter,
    ConversionResult,
    json_to_yaml,
    json_to_xml,
    json_to_csv,
    yaml_to_json,
    csv_to_json,
)

logger = logging.getLogger(__name__)


def get_env_var(key: str, default: Any = None, required: bool = False) -> Any:
    """
    Get environment variable with optional default and required check.

    Args:
        key: Environment variable name
        default: Default value if not found
        required: If True, raise ValueError if not found

    Returns:
        Environment variable value or default

    Raises:
        ValueError: If required=True and variable not found
    """
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


def load_config(config_path: str = None) -> dict:
    """
    Load configuration from file or environment.

    Args:
        config_path: Path to config file (JSON or YAML)

    Returns:
        Configuration dictionary
    """
    config = {}

    if config_path and os.path.exists(config_path):
        import json
        with open(config_path, 'r') as f:
            if config_path.endswith('.json'):
                config = json.load(f)
            elif config_path.endswith(('.yaml', '.yml')):
                try:
                    import yaml
                    config = yaml.safe_load(f)
                except ImportError:
                    logger.warning("PyYAML not installed. Install with: pip install pyyaml")

    return config
