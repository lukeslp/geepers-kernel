#!/usr/bin/env python3
"""
MCP HTTP-to-Stdio Bridge

Bridges Cursor/Codex stdio MCP interface to remote HTTP MCP server.
Allows Cursor to use remote Dreamwalker MCP server as if it were local.

Usage:
    python mcp_http_bridge.py [--url https://dr.eamer.dev/mcp]

Configuration in Cursor:
    {
      "mcpServers": {
        "dreamwalker": {
          "command": "python3",
          "args": ["/home/coolhand/shared/mcp/mcp_http_bridge.py"],
          "env": {}
        }
      }
    }
"""

import sys
import json
import requests
import argparse
import logging
from typing import Dict, Any

# Configure logging to stderr (stdout is for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# MCP server URL
DEFAULT_MCP_URL = "https://dr.eamer.dev/mcp"


class MCPHttpBridge:
    """Bridge between MCP stdio and HTTP protocols."""

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url.rstrip('/')
        self.session = requests.Session()
        logger.info(f"Initialized MCP bridge to: {self.mcp_url}")

    def list_tools(self) -> Dict[str, Any]:
        """List available tools from remote MCP server."""
        try:
            response = self.session.get(f"{self.mcp_url}/tools", timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Listed {data.get('count', 0)} tools")
            return data
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            raise

    def list_resources(self) -> Dict[str, Any]:
        """List available resources from remote MCP server."""
        try:
            response = self.session.get(f"{self.mcp_url}/resources", timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Listed {data.get('count', 0)} resources")
            return data
        except Exception as e:
            logger.error(f"Error listing resources: {e}")
            raise

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the remote MCP server."""
        try:
            logger.info(f"Calling tool: {tool_name}")
            response = self.session.post(
                f"{self.mcp_url}/tools/{tool_name}",
                json=arguments,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Tool {tool_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP stdio request and route to HTTP endpoint."""
        method = request.get('method')
        request_id = request.get('id', 1)

        try:
            if method == 'initialize':
                # Initialization request
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {
                            "name": "dreamwalker-http-bridge",
                            "version": "2.0.0"
                        },
                        "capabilities": {
                            "tools": {},
                            "resources": {}
                        }
                    }
                }

            elif method == 'tools/list':
                tools_data = self.list_tools()
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": tools_data.get('tools', [])
                    }
                }

            elif method == 'resources/list':
                resources_data = self.list_resources()
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "resources": resources_data.get('resources', [])
                    }
                }

            elif method == 'tools/call':
                params = request.get('params', {})
                tool_name = params.get('name')
                arguments = params.get('arguments', {})

                result = self.call_tool(tool_name, arguments)

                # Format result for MCP
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }

        except Exception as e:
            logger.exception(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }

    def run(self):
        """Run the stdio bridge - read from stdin, write to stdout."""
        logger.info("MCP HTTP bridge started, waiting for requests...")

        while True:
            try:
                # Read JSON-RPC request from stdin
                line = sys.stdin.readline()
                if not line:
                    logger.info("EOF received, exiting")
                    break

                line = line.strip()
                if not line:
                    continue

                request = json.loads(line)
                logger.debug(f"Received request: {request.get('method')}")

                # Handle request
                response = self.handle_request(request)

                # Write response to stdout
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
            except KeyboardInterrupt:
                logger.info("Interrupted, exiting")
                break
            except Exception as e:
                logger.exception(f"Error in main loop: {e}")


def main():
    parser = argparse.ArgumentParser(description='MCP HTTP-to-stdio bridge for Dreamwalker')
    parser.add_argument(
        '--url',
        default=DEFAULT_MCP_URL,
        help=f'MCP server URL (default: {DEFAULT_MCP_URL})'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Verify connectivity (lists tools/resources) and exit'
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Starting Dreamwalker MCP HTTP bridge")
    logger.info(f"Target server: {args.url}")

    bridge = MCPHttpBridge(args.url)

    try:
        if args.check:
            try:
                tools = bridge.list_tools()
                resources = bridge.list_resources()
                summary = {
                    "url": bridge.mcp_url,
                    "tool_count": tools.get("count", len(tools.get("tools", []))),
                    "resource_count": resources.get("count", len(resources.get("resources", []))),
                    "tools": tools.get("tools", []),
                    "resources": resources.get("resources", [])
                }
                print(json.dumps(summary, indent=2))
                return
            except Exception as exc:
                logger.error("Connectivity check failed: %s", exc)
                sys.exit(1)

        bridge.run()
    except KeyboardInterrupt:
        logger.info("Bridge stopped")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

