#!/usr/bin/env python3
"""
Utilities MCP Server (Stdio)

Exposes ArXiv, TTS, citations, Semantic Scholar via MCP stdio protocol.

Author: Luke Steuber
"""

import sys
import json
import logging
from typing import Dict, Any


from shared.mcp.utility_server import UtilityServer
from shared.config import ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_mcp_request(server: UtilityServer, request: Dict[str, Any]) -> Dict[str, Any]:
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
                        "name": "geepers-utility",
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
            if hasattr(server, f'tool_{tool_name}'):
                result = getattr(server, f'tool_{tool_name}')(arguments)
                return {"jsonrpc": "2.0", "id": request.get('id'), "result": result}
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            }
    except Exception as e:
        logger.exception(f"Error: {e}")
        return {"jsonrpc": "2.0", "id": request.get('id'), "error": {"code": -32603, "message": str(e)}}


def main():
    logger.info("Starting Utilities MCP Server (stdio)")
    config = ConfigManager(app_name='geepers_utility_mcp')
    server = UtilityServer(config_manager=config)

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
