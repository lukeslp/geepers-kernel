#!/usr/bin/env python3
"""
Unified Orchestrator MCP Server (Stdio)

Exposes Beltalowda and Swarm orchestrators via MCP stdio protocol.

Author: Luke Steuber
"""

import sys
import json
import asyncio
import logging
from typing import Dict, Any

# Add parent to path for imports
sys.path.insert(0, '/home/coolhand/geepers')

from geepers.mcp.unified_server import UnifiedMCPServer
from geepers.config import ConfigManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def handle_mcp_request(server: UnifiedMCPServer, request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle MCP protocol request.

    Args:
        server: UnifiedMCPServer instance
        request: MCP request dict

    Returns:
        MCP response dict
    """
    method = request.get('method')
    params = request.get('params', {})

    try:
        if method == 'initialize':
            # Handle MCP initialization handshake
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {}
                    },
                    "serverInfo": {
                        "name": "geepers-unified",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == 'notifications/initialized' or method == 'initialized':
            # Client confirms initialization complete - Notification, no response
            return None
        
        elif method == 'tools/list':
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": {"tools": server.get_tools_manifest()}
            }

        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})

            # Map tool calls to server methods (both new and legacy names)
            tool_method_map = {
                # New names (geepers_type_name pattern)
                'geepers_orchestrate_cascade': server.tool_dream_orchestrate_research,
                'geepers_orchestrate_swarm': server.tool_dream_orchestrate_search,
                'geepers_utility_status': server.tool_geepers_status,
                'geepers_utility_cancel': server.tool_geepers_cancel,
                'geepers_utility_patterns': server.tool_geepers_patterns,
                'geepers_utility_registry_list': server.tool_geepers_list_tools,
                'geepers_utility_registry_execute': server.tool_geepers_execute_tool,
                # Legacy names for backward compatibility
                'dream_orchestrate_research': server.tool_dream_orchestrate_research,
                'dream_orchestrate_search': server.tool_dream_orchestrate_search,
                'geepers_status': server.tool_geepers_status,
                'geepers_cancel': server.tool_geepers_cancel,
                'geepers_patterns': server.tool_geepers_patterns,
                'geepers_list_tools': server.tool_geepers_list_tools,
                'geepers_execute_tool': server.tool_geepers_execute_tool,
                # Old stdio names
                'orchestrate_research': server.tool_dream_orchestrate_research,
                'orchestrate_search': server.tool_dream_orchestrate_search,
                'get_orchestration_status': server.tool_geepers_status,
                'cancel_orchestration': server.tool_geepers_cancel,
                'list_orchestrator_patterns': server.tool_geepers_patterns,
                'list_registered_tools': server.tool_geepers_list_tools,
                'execute_registered_tool': server.tool_geepers_execute_tool,
            }

            if tool_name in tool_method_map:
                result = await tool_method_map[tool_name](arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "result": result
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }

        elif method == 'resources/list':
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": {"resources": server.get_resources_manifest()}
            }

        elif method == 'resources/read':
            uri = params.get('uri')

            # Support both new and legacy URI formats
            if uri.startswith('orchestrator://'):
                # Legacy format - still support it
                if uri.endswith('/info'):
                    result = await server.resource_orchestrator_info(uri)
                elif '/status' in uri:
                    result = await server.resource_workflow_status(uri)
                elif '/results' in uri:
                    result = await server.resource_workflow_results(uri)
                else:
                    result = {"uri": uri, "error": "Unknown resource"}
            elif uri.startswith('geepers://'):
                # New format
                if uri.endswith('/info'):
                    result = await server.resource_orchestrator_info(uri)
                elif '/status' in uri:
                    result = await server.resource_workflow_status(uri)
                elif '/results' in uri:
                    result = await server.resource_workflow_results(uri)
                else:
                    result = {"uri": uri, "error": "Unknown resource"}
            else:
                result = {"uri": uri, "error": "Unknown resource"}

            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": result
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            }

    except Exception as e:
        logger.exception(f"Error handling request: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request.get('id'),
            "error": {"code": -32603, "message": str(e)}
        }


async def main():
    """Main stdio loop for MCP server."""
    logger.info("Starting Unified Orchestrator MCP Server (stdio)")

    # Initialize server
    config = ConfigManager(app_name='geepers_unified_mcp')
    server = UnifiedMCPServer(config_manager=config)

    # Read requests from stdin, write responses to stdout
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = await handle_mcp_request(server, request)

            if response is not None:
                # Write response to stdout
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.exception(f"Error in main loop: {e}")


if __name__ == '__main__':
    asyncio.run(main())
