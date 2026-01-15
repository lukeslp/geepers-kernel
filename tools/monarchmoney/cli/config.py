"""Configuration management for Monarch Money CLI."""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

CONFIG_FILE = Path.home() / ".mm" / "config.yaml"

DEFAULT_CONFIG = {
    "defaults": {
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-5-20250929",
        "transaction_limit": 100,
        "date_range_days": 30,
    },
    "display": {
        "show_icons": True,
        "table_style": "rounded",
        "color_enabled": True,
    },
    "cache": {
        "enabled": True,
        "ttl_seconds": 300,
    },
    "aliases": {
        # User can add custom command aliases here
        # Example: "spending": "insights ask 'Show my spending by category'"
    }
}

def load_config() -> Dict[str, Any]:
    """Load config from file or return defaults."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE) as f:
            config = yaml.safe_load(f) or {}

        # Merge with defaults to ensure all keys exist
        merged = DEFAULT_CONFIG.copy()
        for key in config:
            if isinstance(config[key], dict) and key in merged:
                merged[key].update(config[key])
            else:
                merged[key] = config[key]

        return merged
    except Exception:
        # If config file is corrupt, return defaults
        return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]) -> None:
    """Save config to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

def get_default(key: str, default: Optional[Any] = None) -> Any:
    """Get a default value from config.

    Args:
        key: Dot-separated key path (e.g., 'defaults.llm_provider')
        default: Fallback value if key not found

    Returns:
        Config value or default
    """
    config = load_config()
    keys = key.split('.')
    value = config

    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default

    return value if value is not None else default

def set_config_value(key: str, value: Any) -> None:
    """Set a config value.

    Args:
        key: Dot-separated key path (e.g., 'defaults.llm_provider')
        value: Value to set
    """
    config = load_config()
    keys = key.split('.')

    # Navigate to the parent dict
    target = config
    for k in keys[:-1]:
        if k not in target:
            target[k] = {}
        target = target[k]

    # Set the value
    target[keys[-1]] = value

    save_config(config)
