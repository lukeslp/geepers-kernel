#!/usr/bin/env python3
"""
Data Fetching MCP Server (Stdio)

Exposes data fetching clients via MCP stdio protocol.

Author: Luke Steuber
"""

import sys
import json
import logging
from typing import Dict, Any

# Add parent to path for imports

from shared.mcp.data_server import DataServer
from shared.config import ConfigManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def handle_mcp_request(server: DataServer, request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP protocol request."""
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
                        "name": "geepers-data",
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

            # Call the appropriate tool method
            if hasattr(server, f'tool_{tool_name}'):
                result = getattr(server, f'tool_{tool_name}')(arguments)
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
            result = server.read_resource(uri)
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
    logger.info("Starting Data Fetching MCP Server (stdio)")

    config = ConfigManager(app_name='geepers_data_mcp')
    server = DataServer(config_manager=config)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = handle_mcp_request(server, request)

            if response is not None:
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.exception(f"Error in main loop: {e}")


if __name__ == '__main__':
    main()
