"""
Discovery MCP Resources

Provides special MCP resources for tool and provider discovery.

Resources provided:
- shared://tools/catalog - Complete tool catalog
- shared://tools/category/{category} - Tools by category
- shared://providers/status - Provider availability
- shared://providers/capabilities - Provider capability matrix
- shared://costs/estimates - Cost estimation data

Author: Luke Steuber
Date: 2025-11-20
"""

import logging
from typing import Dict, List, Any, Optional
import sys

sys.path.insert(0, '/home/coolhand/shared')
from config import ConfigManager
from llm_providers.factory import ProviderFactory, PROVIDER_CAPABILITIES
from .tool_metadata import TOOL_METADATA, get_tools_by_category

logger = logging.getLogger(__name__)


class DiscoveryResources:
    """Provides MCP resources for discovering capabilities."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize discovery resources."""
        self.config = config_manager or ConfigManager(app_name='mcp_discovery')
    
    def resource_tools_catalog(self) -> Dict[str, Any]:
        """
        Resource: shared://tools/catalog
        
        Complete catalog of all available tools.
        """
        tools_by_category = {}
        for category in ['llm', 'data', 'cache', 'utility', 'orchestration']:
            tools_by_category[category] = get_tools_by_category(category)
        
        return {
            "uri": "shared://tools/catalog",
            "total_tools": sum(len(tools) for tools in tools_by_category.values()),
            "categories": tools_by_category,
            "metadata": {
                "llm": "LLM provider operations",
                "data": "Data fetching from external sources",
                "cache": "Redis caching operations",
                "utility": "Document parsing, citations, utilities",
                "orchestration": "Multi-agent workflow orchestration"
            }
        }
    
    def resource_tools_by_category(self, category: str) -> Dict[str, Any]:
        """
        Resource: shared://tools/category/{category}
        
        Tools in a specific category with full metadata.
        """
        tool_names = get_tools_by_category(category)
        tools_with_meta = []
        
        for name in tool_names:
            meta = TOOL_METADATA.get(name, {})
            tools_with_meta.append({
                "name": name,
                **meta
            })
        
        return {
            "uri": f"shared://tools/category/{category}",
            "category": category,
            "tool_count": len(tools_with_meta),
            "tools": tools_with_meta
        }
    
    def resource_providers_status(self) -> Dict[str, Any]:
        """
        Resource: shared://providers/status
        
        Provider availability and configuration status.
        """
        available = self.config.list_available_providers()
        all_providers = ProviderFactory.list_providers()
        
        provider_status = {}
        for provider in all_providers:
            has_key = provider in available
            provider_status[provider] = {
                "configured": has_key,
                "capabilities": PROVIDER_CAPABILITIES.get(provider, {}),
                "models": []  # Could list models if provider created
            }
        
        return {
            "uri": "shared://providers/status",
            "total_providers": len(all_providers),
            "configured_providers": len(available),
            "providers": provider_status,
            "missing_keys": [p for p in all_providers if p not in available]
        }
    
    def resource_providers_capabilities(self) -> Dict[str, Any]:
        """
        Resource: shared://providers/capabilities
        
        Capability matrix showing what each provider can do.
        """
        return {
            "uri": "shared://providers/capabilities",
            "capabilities": PROVIDER_CAPABILITIES,
            "by_capability": {
                "chat": ProviderFactory.find_providers_with_capability('chat'),
                "streaming": ProviderFactory.find_providers_with_capability('streaming'),
                "vision": ProviderFactory.find_providers_with_capability('vision'),
                "image_generation": ProviderFactory.find_providers_with_capability('image_generation'),
                "tts": ProviderFactory.find_providers_with_capability('tts'),
                "embedding": ProviderFactory.find_providers_with_capability('embedding')
            }
        }
    
    def resource_cost_estimates(self) -> Dict[str, Any]:
        """
        Resource: shared://costs/estimates
        
        Cost estimation data for all tools.
        """
        cost_data = {}
        for tool_name, meta in TOOL_METADATA.items():
            cost_estimate = meta.get('cost_estimate', {})
            if cost_estimate.get('max', 0) > 0:
                cost_data[tool_name] = cost_estimate
        
        return {
            "uri": "shared://costs/estimates",
            "tools_with_costs": len(cost_data),
            "estimates": cost_data,
            "currency": "USD",
            "notes": "Estimates are approximate and depend on usage patterns"
        }
    
    def get_resources_manifest(self) -> List[Dict[str, Any]]:
        """Get list of discovery resources."""
        return [
            {
                "uri": "shared://tools/catalog",
                "name": "Tool Catalog",
                "description": "Complete catalog of all available MCP tools",
                "mimeType": "application/json"
            },
            {
                "uri": "shared://tools/category/{category}",
                "name": "Tools by Category",
                "description": "Tools in specific category (llm, data, cache, utility, orchestration)",
                "mimeType": "application/json"
            },
            {
                "uri": "shared://providers/status",
                "name": "Provider Status",
                "description": "Provider availability and configuration status",
                "mimeType": "application/json"
            },
            {
                "uri": "shared://providers/capabilities",
                "name": "Provider Capabilities",
                "description": "Capability matrix showing what each provider supports",
                "mimeType": "application/json"
            },
            {
                "uri": "shared://costs/estimates",
                "name": "Cost Estimates",
                "description": "Estimated costs for tool execution",
                "mimeType": "application/json"
            }
        ]
    
    def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a discovery resource by URI.
        
        Args:
            uri: Resource URI
        
        Returns:
            Resource content
        """
        try:
            if uri == "shared://tools/catalog":
                return self.resource_tools_catalog()
            
            elif uri.startswith("shared://tools/category/"):
                category = uri.replace("shared://tools/category/", "")
                return self.resource_tools_by_category(category)
            
            elif uri == "shared://providers/status":
                return self.resource_providers_status()
            
            elif uri == "shared://providers/capabilities":
                return self.resource_providers_capabilities()
            
            elif uri == "shared://costs/estimates":
                return self.resource_cost_estimates()
            
            else:
                return {
                    "uri": uri,
                    "error": "Unknown discovery resource"
                }
        
        except Exception as e:
            logger.exception(f"Error reading discovery resource {uri}: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }


__all__ = ['DiscoveryResources']
