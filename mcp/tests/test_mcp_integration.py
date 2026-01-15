"""
Integration Tests for MCP Server

Tests the complete MCP server stack including stdio protocol, tool execution,
and resource access.

Author: Luke Steuber
Date: 2025-11-20
"""

import pytest
import asyncio
import json
import sys
from pathlib import Path

# Add shared library to path
sys.path.insert(0, '/home/coolhand/shared')

from mcp.master_server import MasterMCPServer, get_master_server
from mcp.tool_metadata import get_tool_metadata, get_tools_by_category, get_cost_estimate
from mcp.discovery_resources import DiscoveryResources
from config import ConfigManager


class TestMasterServer:
    """Test master MCP server functionality."""
    
    @pytest.fixture
    def server(self):
        """Create test server instance."""
        config = ConfigManager(app_name='mcp_test')
        return MasterMCPServer(config_manager=config)
    
    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """Test tool listing."""
        tools = await server.list_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 20, "Should have at least 20 tools"
        
        # Check tool structure
        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool
            assert 'category' in tool
    
    @pytest.mark.asyncio
    async def test_list_resources(self, server):
        """Test resource listing."""
        resources = await server.list_resources()
        
        assert isinstance(resources, list)
        assert len(resources) > 5, "Should have multiple resources"
        
        # Check resource structure
        for resource in resources:
            assert 'uri' in resource
            assert 'name' in resource
            assert 'mimeType' in resource
    
    @pytest.mark.asyncio
    async def test_get_server_info(self, server):
        """Test server info retrieval."""
        info = await server.get_server_info()
        
        assert info['name'] == "Shared Library MCP Server"
        assert info['version'] == "1.0.0"
        assert info['tools_count'] > 20
        assert 'tools_by_category' in info
        assert 'providers_available' in info
    
    def test_categorize_tool(self, server):
        """Test tool categorization."""
        assert server._categorize_tool('chat_completion') == 'llm'
        assert server._categorize_tool('dream_of_arxiv') == 'data'
        assert server._categorize_tool('cache_get') == 'cache'
        assert server._categorize_tool('parse_document') == 'utility'
        assert server._categorize_tool('dream_research') == 'orchestration'
    
    def test_singleton_pattern(self):
        """Test master server singleton."""
        server1 = get_master_server()
        server2 = get_master_server()
        
        assert server1 is server2, "Should return same instance"


class TestToolMetadata:
    """Test tool metadata functionality."""
    
    def test_get_tool_metadata(self):
        """Test metadata retrieval."""
        meta = get_tool_metadata('chat_completion')
        
        assert meta['category'] == 'llm'
        assert 'description' in meta
        assert 'cost_estimate' in meta
        assert 'execution_time' in meta
        assert 'use_cases' in meta
        assert 'examples' in meta
    
    def test_get_tools_by_category(self):
        """Test category filtering."""
        llm_tools = get_tools_by_category('llm')
        assert 'chat_completion' in llm_tools
        assert 'create_provider' in llm_tools
        
        data_tools = get_tools_by_category('data')
        assert 'dream_of_arxiv' in data_tools
        
        cache_tools = get_tools_by_category('cache')
        assert 'cache_get' in cache_tools
    
    def test_get_cost_estimate(self):
        """Test cost estimation."""
        cost = get_cost_estimate('dream_research')
        
        assert 'min' in cost
        assert 'max' in cost
        assert 'avg' in cost
        assert cost['avg'] > 0


class TestDiscoveryResources:
    """Test discovery resource functionality."""
    
    @pytest.fixture
    def discovery(self):
        """Create discovery resources instance."""
        return DiscoveryResources()
    
    def test_tools_catalog(self, discovery):
        """Test tools catalog resource."""
        catalog = discovery.resource_tools_catalog()
        
        assert catalog['uri'] == 'shared://tools/catalog'
        assert 'categories' in catalog
        assert catalog['total_tools'] > 20
    
    def test_tools_by_category(self, discovery):
        """Test category resource."""
        llm_tools = discovery.resource_tools_by_category('llm')
        
        assert llm_tools['category'] == 'llm'
        assert llm_tools['tool_count'] > 0
        assert 'tools' in llm_tools
    
    def test_providers_status(self, discovery):
        """Test provider status resource."""
        status = discovery.resource_providers_status()
        
        assert status['uri'] == 'shared://providers/status'
        assert 'providers' in status
        assert 'total_providers' in status
    
    def test_providers_capabilities(self, discovery):
        """Test provider capabilities resource."""
        caps = discovery.resource_providers_capabilities()
        
        assert caps['uri'] == 'shared://providers/capabilities'
        assert 'capabilities' in caps
        assert 'by_capability' in caps
        assert 'vision' in caps['by_capability']
    
    def test_cost_estimates(self, discovery):
        """Test cost estimates resource."""
        costs = discovery.resource_cost_estimates()
        
        assert costs['uri'] == 'shared://costs/estimates'
        assert 'estimates' in costs
        assert costs['currency'] == 'USD'


class TestStdioProtocol:
    """Test stdio protocol implementation."""
    
    @pytest.mark.asyncio
    async def test_ping_message(self):
        """Test basic ping/pong."""
        # This would require running the stdio server and sending messages
        # Placeholder for now
        pass
    
    @pytest.mark.asyncio
    async def test_initialize_message(self):
        """Test initialization protocol."""
        # Placeholder
        pass
    
    @pytest.mark.asyncio
    async def test_list_tools_message(self):
        """Test tools/list message."""
        # Placeholder
        pass


@pytest.mark.slow
class TestIntegration:
    """Integration tests requiring API keys and external services."""
    
    @pytest.mark.asyncio
    async def test_chat_completion_anthropic(self, server):
        """Test actual chat completion (requires API key)."""
        # Skip if no API key
        config = ConfigManager()
        if not config.has_api_key('anthropic'):
            pytest.skip("ANTHROPIC_API_KEY not set")
        
        result = await server.call_tool('chat_completion', {
            'provider_name': 'anthropic',
            'messages': [{'role': 'user', 'content': 'Say hello'}],
            'max_tokens': 10
        })
        
        assert result['success'] == True
        assert 'content' in result
    
    @pytest.mark.asyncio
    async def test_cache_operations(self, server):
        """Test cache set/get cycle."""
        # Set
        result = await server.call_tool('cache_set', {
            'key': 'test_key',
            'value': 'test_value',
            'ttl': 60
        })
        assert result['success'] == True
        
        # Get
        result = await server.call_tool('cache_get', {
            'key': 'test_key'
        })
        assert result['success'] == True
        assert result['value'] == 'test_value'
        
        # Delete
        result = await server.call_tool('cache_delete', {
            'key': 'test_key'
        })
        assert result['success'] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
