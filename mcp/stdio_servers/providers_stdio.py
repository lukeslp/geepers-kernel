#!/usr/bin/env python3
"""
Providers MCP Server (Stdio)

Exposes LLM provider capabilities via MCP stdio protocol.

Author: Luke Steuber
"""

import sys
import json
import asyncio
import logging
from typing import Dict, Any

# Add parent to path for imports
sys.path.insert(0, '/home/coolhand/geepers')

from geepers.mcp.providers_server import ProvidersServer
from geepers.config import ConfigManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def handle_mcp_request(server: ProvidersServer, request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle MCP protocol request.

    Args:
        server: ProvidersServer instance
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
                        "name": "geepers-providers",
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

            # Map tool calls to server methods
            tool_method_map = {
                'create_provider': server.tool_create_provider,
                'list_provider_models': server.tool_list_provider_models,
                'chat_completion': server.tool_chat_completion,
                'generate_image': server.tool_generate_image,
                'analyze_image': server.tool_analyze_image,
            }

            if tool_name in tool_method_map:
                result = tool_method_map[tool_name](arguments)
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

            # Route to appropriate resource handler
            if uri.endswith('/info'):
                result = server.resource_provider_info(uri)
            elif uri.endswith('/models'):
                result = server.resource_provider_models(uri)
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


def main():
    """Main stdio loop for MCP server."""
    logger.info("Starting Providers MCP Server (stdio)")

    # Initialize server
    config = ConfigManager(app_name='geepers_providers_mcp')
    server = ProvidersServer(config_manager=config)

    # Read requests from stdin, write responses to stdout
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = handle_mcp_request(server, request)

            if response is not None:
                # Write response to stdout
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.exception(f"Error in main loop: {e}")


if __name__ == '__main__':
    main()
