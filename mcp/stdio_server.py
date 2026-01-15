#!/usr/bin/env python3
"""
stdio MCP Server for Local AI Assistant Integration

This server implements the MCP protocol over stdio (standard input/output) for use with
AI coding assistants like Claude Code and Cursor. It exposes all shared library capabilities
through a unified interface.

Usage:
    # Direct execution
    python stdio_server.py
    
    # In Claude Code config (claude_desktop_config.json):
    {
      "mcpServers": {
        "shared-library": {
          "command": "python",
          "args": ["/home/coolhand/shared/mcp/stdio_server.py"],
          "env": {
            "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
            "OPENAI_API_KEY": "${OPENAI_API_KEY}",
            "XAI_API_KEY": "${XAI_API_KEY}"
          }
        }
      }
    }

Author: Luke Steuber
Date: 2025-11-20
"""

import sys
import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional

# Add shared library to path
sys.path.insert(0, '/home/coolhand/shared')

# Import master server
from mcp.master_server import get_master_server
from config import ConfigManager

# Setup logging to stderr (stdout is used for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('mcp.stdio')


class StdioMCPServer:
    """
    MCP server implementation using stdio protocol.
    
    This server reads JSON-RPC messages from stdin and writes responses to stdout,
    following the Model Context Protocol specification.
    """
    
    def __init__(self):
        """Initialize stdio MCP server."""
        self.config = ConfigManager(app_name='mcp_stdio')
        self.master_server = get_master_server(config_manager=self.config)
        self.running = False
        logger.info("stdio MCP server initialized")
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an incoming MCP message.
        
        Args:
            message: JSON-RPC message
        
        Returns:
            Response message
        """
        method = message.get('method')
        params = message.get('params', {})
        msg_id = message.get('id')
        
        logger.debug(f"Handling method: {method}")
        
        try:
            # Handle different MCP methods
            if method == 'initialize':
                result = await self._handle_initialize(params)
            
            elif method == 'tools/list':
                result = await self._handle_list_tools(params)
            
            elif method == 'tools/call':
                result = await self._handle_call_tool(params)
            
            elif method == 'resources/list':
                result = await self._handle_list_resources(params)
            
            elif method == 'resources/read':
                result = await self._handle_read_resource(params)
            
            elif method == 'ping':
                result = {'status': 'ok'}
            
            else:
                return {
                    'jsonrpc': '2.0',
                    'id': msg_id,
                    'error': {
                        'code': -32601,
                        'message': f'Method not found: {method}'
                    }
                }
            
            return {
                'jsonrpc': '2.0',
                'id': msg_id,
                'result': result
            }
        
        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            return {
                'jsonrpc': '2.0',
                'id': msg_id,
                'error': {
                    'code': -32603,
                    'message': str(e)
                }
            }
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        logger.info("Initializing MCP server")
        
        server_info = await self.master_server.get_server_info()
        
        return {
            'protocolVersion': '2024-11-05',
            'capabilities': {
                'tools': {},
                'resources': {},
            },
            'serverInfo': {
                'name': server_info['name'],
                'version': server_info['version']
            }
        }
    
    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        logger.info("Listing tools")
        tools = await self.master_server.list_tools()
        return {'tools': tools}
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        logger.info(f"Calling tool: {tool_name}")
        
        result = await self.master_server.call_tool(tool_name, arguments)
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(result, indent=2)
                }
            ]
        }
    
    async def _handle_list_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request."""
        logger.info("Listing resources")
        resources = await self.master_server.list_resources()
        return {'resources': resources}
    
    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get('uri')
        
        logger.info(f"Reading resource: {uri}")
        
        content = await self.master_server.read_resource(uri)
        
        return {
            'contents': [
                {
                    'uri': uri,
                    'mimeType': 'application/json',
                    'text': json.dumps(content, indent=2)
                }
            ]
        }
    
    async def run(self):
        """
        Run the stdio MCP server loop.
        
        Reads JSON-RPC messages from stdin and writes responses to stdout.
        """
        logger.info("Starting stdio MCP server...")
        self.running = True
        
        try:
            # Read messages line by line from stdin
            while self.running:
                try:
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, sys.stdin.readline
                    )
                    
                    if not line:
                        # EOF reached
                        logger.info("EOF received, shutting down")
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse JSON-RPC message
                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON: {e}")
                        continue
                    
                    # Handle message
                    response = await self.handle_message(message)
                    
                    # Write response to stdout
                    response_json = json.dumps(response)
                    print(response_json, flush=True)
                    logger.debug(f"Sent response: {response_json[:100]}...")
                
                except Exception as e:
                    logger.exception(f"Error in message loop: {e}")
        
        finally:
            logger.info("stdio MCP server stopped")
            self.running = False


async def main():
    """Main entry point for stdio MCP server."""
    logger.info("=== Shared Library stdio MCP Server ===")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    server = StdioMCPServer()
    
    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception(f"Failed to start server: {e}")
        sys.exit(1)
