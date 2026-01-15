"""
Configuration Management MCP Server

Exposes shared.config capabilities through MCP protocol.

Tools provided:
- get_api_key: Retrieve API key for a provider
- set_api_key: Update API key (encrypted storage)
- list_providers: Show configured providers
- check_provider_status: Test provider connectivity
- get_config_value: Get any config value

Resources provided:
- config://providers: List all configured providers
- config://api_keys: Show which providers have keys

Author: Luke Steuber
"""

import logging
from typing import Dict, List, Optional, Any

# Import from shared library
import sys
sys.path.insert(0, '/home/coolhand/shared')
from config import ConfigManager
from llm_providers.factory import ProviderFactory

logger = logging.getLogger(__name__)


class ConfigServer:
    """
    MCP server for configuration management.
    
    Exposes ConfigManager capabilities through MCP protocol.
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize config MCP server.
        
        Args:
            config_manager: ConfigManager instance (creates new one if None)
        """
        self.config = config_manager or ConfigManager(app_name='mcp_config')
    
    # -------------------------------------------------------------------------
    # MCP Tools
    # -------------------------------------------------------------------------
    
    def tool_get_api_key(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: get_api_key
        
        Retrieve API key for a provider.
        
        Arguments:
            provider (str): Provider name (anthropic, openai, xai, etc.)
            
        Returns:
            {success: bool, has_key: bool, key_preview: str}
        """
        try:
            provider = arguments.get('provider')
            if not provider:
                return {
                    "success": False,
                    "error": "Missing required argument: provider"
                }
            
            api_key = self.config.get_api_key(provider)
            
            if api_key:
                # Show only first 8 and last 4 characters for security
                if len(api_key) > 12:
                    key_preview = f"{api_key[:8]}...{api_key[-4:]}"
                else:
                    key_preview = "***" 
                
                return {
                    "success": True,
                    "has_key": True,
                    "provider": provider,
                    "key_preview": key_preview,
                    "key_length": len(api_key)
                }
            else:
                return {
                    "success": True,
                    "has_key": False,
                    "provider": provider,
                    "message": f"No API key configured for {provider}"
                }
        
        except Exception as e:
            logger.exception(f"Error in get_api_key: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def tool_list_providers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: list_providers
        
        Show all available providers and which have API keys configured.
        
        Arguments:
            None
            
        Returns:
            {success: bool, providers: List[Dict]}
        """
        try:
            # Get all available providers from factory
            all_providers = ProviderFactory.list_providers()
            
            providers_info = []
            for provider_name in sorted(all_providers):
                has_key = self.config.has_api_key(provider_name)
                providers_info.append({
                    "name": provider_name,
                    "configured": has_key
                })
            
            return {
                "success": True,
                "providers": providers_info,
                "total_providers": len(all_providers),
                "configured_providers": sum(1 for p in providers_info if p['configured'])
            }
        
        except Exception as e:
            logger.exception(f"Error in list_providers: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def tool_check_provider_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: check_provider_status
        
        Test provider connectivity by attempting to create an instance.
        
        Arguments:
            provider (str): Provider name
            
        Returns:
            {success: bool, available: bool, message: str}
        """
        try:
            provider = arguments.get('provider')
            if not provider:
                return {
                    "success": False,
                    "error": "Missing required argument: provider"
                }
            
            # Check if API key exists
            if not self.config.has_api_key(provider):
                return {
                    "success": True,
                    "available": False,
                    "provider": provider,
                    "message": f"No API key configured for {provider}"
                }
            
            # Try to create provider instance
            try:
                ProviderFactory.get_provider(provider)
                return {
                    "success": True,
                    "available": True,
                    "provider": provider,
                    "message": f"{provider} is available and configured"
                }
            except Exception as provider_error:
                return {
                    "success": True,
                    "available": False,
                    "provider": provider,
                    "message": f"Provider error: {str(provider_error)}"
                }
        
        except Exception as e:
            logger.exception(f"Error in check_provider_status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def tool_get_config_value(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: get_config_value
        
        Get any configuration value by key.
        
        Arguments:
            key (str): Configuration key
            default (any, optional): Default value if not found
            
        Returns:
            {success: bool, value: Any, found: bool}
        """
        try:
            key = arguments.get('key')
            if not key:
                return {
                    "success": False,
                    "error": "Missing required argument: key"
                }
            
            default = arguments.get('default')
            value = self.config.get(key, default)
            
            # Mask sensitive values
            is_sensitive = any(
                sensitive_word in key.upper() 
                for sensitive_word in ['API_KEY', 'SECRET', 'PASSWORD', 'TOKEN']
            )
            
            if is_sensitive and value:
                display_value = "***REDACTED***"
            else:
                display_value = value
            
            return {
                "success": True,
                "key": key,
                "value": display_value,
                "found": value is not None,
                "is_sensitive": is_sensitive
            }
        
        except Exception as e:
            logger.exception(f"Error in get_config_value: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def tool_list_config_keys(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: list_config_keys
        
        List all configuration keys (without sensitive values).
        
        Arguments:
            filter (str, optional): Filter keys by substring
            
        Returns:
            {success: bool, keys: List[str], count: int}
        """
        try:
            filter_str = arguments.get('filter', '').upper()
            
            all_keys = list(self.config.config.keys())
            
            if filter_str:
                filtered_keys = [k for k in all_keys if filter_str in k.upper()]
            else:
                filtered_keys = all_keys
            
            # Categorize keys
            sensitive_keys = []
            normal_keys = []
            
            for key in sorted(filtered_keys):
                is_sensitive = any(
                    sensitive_word in key.upper() 
                    for sensitive_word in ['API_KEY', 'SECRET', 'PASSWORD', 'TOKEN']
                )
                if is_sensitive:
                    sensitive_keys.append(key)
                else:
                    normal_keys.append(key)
            
            return {
                "success": True,
                "keys": normal_keys,
                "sensitive_keys": [f"{k} (hidden)" for k in sensitive_keys],
                "total_keys": len(filtered_keys),
                "filter_applied": bool(filter_str)
            }
        
        except Exception as e:
            logger.exception(f"Error in list_config_keys: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # -------------------------------------------------------------------------
    # MCP Resources
    # -------------------------------------------------------------------------
    
    def resource_providers_list(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: config://providers
        
        Returns list of all configured providers.
        
        Args:
            uri: Resource URI ("config://providers")
            
        Returns:
            Providers list with configuration status
        """
        try:
            all_providers = ProviderFactory.list_providers()
            
            providers_info = {}
            for provider_name in sorted(all_providers):
                has_key = self.config.has_api_key(provider_name)
                providers_info[provider_name] = {
                    "configured": has_key,
                    "available": has_key
                }
            
            return {
                "uri": uri,
                "providers": providers_info,
                "total_providers": len(all_providers),
                "configured_count": sum(1 for p in providers_info.values() if p['configured'])
            }
        
        except Exception as e:
            logger.exception(f"Error in resource_providers_list: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }
    
    def resource_api_keys_status(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: config://api_keys
        
        Returns which providers have API keys (without revealing keys).
        
        Args:
            uri: Resource URI ("config://api_keys")
            
        Returns:
            API keys status
        """
        try:
            all_providers = ProviderFactory.list_providers()
            
            api_keys_status = {}
            for provider_name in sorted(all_providers):
                has_key = self.config.has_api_key(provider_name)
                api_keys_status[provider_name] = {
                    "configured": has_key,
                    "status": "configured" if has_key else "missing"
                }
            
            configured_providers = [
                p for p, status in api_keys_status.items() 
                if status['configured']
            ]
            missing_providers = [
                p for p, status in api_keys_status.items() 
                if not status['configured']
            ]
            
            return {
                "uri": uri,
                "api_keys": api_keys_status,
                "configured_providers": configured_providers,
                "missing_providers": missing_providers,
                "total_providers": len(all_providers),
                "configured_count": len(configured_providers)
            }
        
        except Exception as e:
            logger.exception(f"Error in resource_api_keys_status: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }
    
    # -------------------------------------------------------------------------
    # MCP Server Interface
    # -------------------------------------------------------------------------
    
    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP tools manifest.
        
        Returns:
            List of tool definitions
        """
        return [
            {
                "name": "get_api_key",
                "description": "Retrieve API key for a provider (masked for security)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "Provider name (anthropic, openai, xai, etc.)"
                        }
                    },
                    "required": ["provider"]
                }
            },
            {
                "name": "list_providers",
                "description": "Show all available providers and configuration status",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "check_provider_status",
                "description": "Test provider connectivity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "Provider name"
                        }
                    },
                    "required": ["provider"]
                }
            },
            {
                "name": "get_config_value",
                "description": "Get configuration value by key (sensitive values masked)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Configuration key"
                        },
                        "default": {
                            "description": "Default value if not found (optional)"
                        }
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "list_config_keys",
                "description": "List all configuration keys",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Filter keys by substring (optional)"
                        }
                    }
                }
            }
        ]
    
    def get_resources_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP resources manifest.
        
        Returns:
            List of resource templates
        """
        return [
            {
                "uri": "config://providers",
                "name": "Providers List",
                "description": "All available providers with configuration status",
                "mimeType": "application/json"
            },
            {
                "uri": "config://api_keys",
                "name": "API Keys Status",
                "description": "Which providers have API keys configured",
                "mimeType": "application/json"
            }
        ]

