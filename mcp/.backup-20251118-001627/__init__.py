"""
MCP (Model Context Protocol) Server Foundation

Exposes shared library capabilities through MCP protocol for external integrations.

Modules:
- providers_server.py: LLM provider tools and resources
- config_server.py: Configuration management resources
- tools_server.py: Tool registry and execution
- unified_server.py: Unified orchestrator MCP server
- streaming.py: SSE bridge and webhook infrastructure

Usage:
    from shared.mcp import UnifiedMCPServer, ProvidersServer
    from shared.mcp import get_streaming_bridge, get_webhook_manager

    # Create MCP servers
    orchestrator_mcp = UnifiedMCPServer()
    providers_mcp = ProvidersServer()

    # Access streaming infrastructure
    stream_bridge = get_streaming_bridge()
    webhook_mgr = get_webhook_manager()
"""

from .streaming import (
    StreamingBridge,
    WebhookManager,
    get_streaming_bridge,
    get_webhook_manager
)

from .unified_server import UnifiedMCPServer

from .streaming_endpoint import (
    create_streaming_blueprint,
    register_streaming_routes
)

from .tool_registry import (
    ToolRegistry,
    ToolDefinition,
    ToolParameter,
    get_tool_registry
)

__all__ = [
    # MCP Servers
    'UnifiedMCPServer',
    'ProvidersServer',
    'ConfigServer',
    'ToolsServer',

    # Streaming Infrastructure
    'StreamingBridge',
    'WebhookManager',
    'get_streaming_bridge',
    'get_webhook_manager',

    # Flask Integration
    'create_streaming_blueprint',
    'register_streaming_routes',

    # Tool Registry
    'ToolRegistry',
    'ToolDefinition',
    'ToolParameter',
    'get_tool_registry',
]
