"""
Master MCP Server

Unified MCP server that combines all sub-servers (providers, data, cache, utility, orchestration)
into a single interface for AI coding assistants like Claude Code and Cursor.

Author: Luke Steuber
Date: 2025-11-20
"""

import logging
from typing import Dict, List, Optional, Any
import asyncio

# Import sub-servers
from .providers_server import ProvidersServer
from .data_server import DataServer
from .cache_server import CacheServer
from .utility_server import UtilityServer
from .unified_server import UnifiedMCPServer as OrchestrationServer

# Import metadata enrichment
from .tool_metadata import enrich_tool_manifest

# Import shared library
import sys
sys.path.insert(0, '/home/coolhand/shared')
from config import ConfigManager

logger = logging.getLogger(__name__)


class MasterMCPServer:
    """Master MCP server exposing all shared library capabilities."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize master MCP server."""
        self.config = config_manager or ConfigManager(app_name='mcp_master')
        
        # Initialize sub-servers
        logger.info("Initializing sub-servers...")
        self.providers_server = ProvidersServer(config_manager=self.config)
        self.data_server = DataServer(config_manager=self.config)
        self.cache_server = CacheServer(config_manager=self.config)
        self.utility_server = UtilityServer(config_manager=self.config)
        self.orchestration_server = OrchestrationServer(config_manager=self.config)
        
        # Cache for tool manifests
        self._tools_cache = None
        self._resources_cache = None
        
        logger.info("Master MCP server initialized successfully")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from all sub-servers."""
        if self._tools_cache is not None:
            return self._tools_cache
        
        tools = []
        
        # Collect tools from each sub-server
        try:
            tools.extend(self.providers_server.get_tools_manifest())
        except Exception as e:
            logger.error(f"Error getting provider tools: {e}")
        
        try:
            tools.extend(self.data_server.get_tools_manifest())
        except Exception as e:
            logger.error(f"Error getting data tools: {e}")
        
        try:
            tools.extend(self.cache_server.get_tools_manifest())
        except Exception as e:
            logger.error(f"Error getting cache tools: {e}")
        
        try:
            tools.extend(self.utility_server.get_tools_manifest())
        except Exception as e:
            logger.error(f"Error getting utility tools: {e}")
        
        # Add metadata tags
        for tool in tools:
            if 'category' not in tool:
                tool['category'] = self._categorize_tool(tool['name'])
        
        # Enrich with additional metadata
        tools = enrich_tool_manifest(tools)
        
        logger.info(f"Total tools available: {len(tools)}")
        self._tools_cache = tools
        return tools
    
    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize a tool based on its name."""
        if tool_name in ['create_provider', 'list_provider_models', 'chat_completion', 
                        'generate_image', 'analyze_image']:
            return 'llm'
        elif tool_name.startswith('dream_of_'):
            return 'data'
        elif tool_name.startswith('cache_'):
            return 'cache'
        elif tool_name in ['parse_document', 'multi_provider_search', 'extract_citations', 
                          'format_citation_bibtex']:
            return 'utility'
        elif tool_name.startswith(('dream_research', 'dream_search', 'dreamwalker_')):
            return 'orchestration'
        else:
            return 'other'


# Singleton instance
_master_server_instance = None


def get_master_server(config_manager: Optional[ConfigManager] = None) -> MasterMCPServer:
    """Get singleton master MCP server instance."""
    global _master_server_instance
    
    if _master_server_instance is None:
        _master_server_instance = MasterMCPServer(config_manager=config_manager)
    
    return _master_server_instance


__all__ = ['MasterMCPServer', 'get_master_server']
