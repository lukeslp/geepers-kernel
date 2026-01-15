#!/usr/bin/env python3
"""
HTTP/SSE wrapper for Monarch Money MCP Server.
Allows remote access from Claude Desktop or web clients.
"""

import asyncio
import sys
from aiohttp import web
from mcp.server.sse import SseServerTransport
from mcp.server import Server

sys.path.insert(0, '/home/coolhand/tools/monarchmoney')
from mcp_server.server import app, list_tools, call_tool

async def handle_sse(request):
    """Handle SSE connection for MCP."""
    async with SseServerTransport("/messages") as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )
    return web.Response()

async def handle_messages(request):
    """Handle MCP messages over HTTP POST."""
    # This endpoint is used by SSE transport for message passing
    return web.Response(text="OK")

async def create_app():
    """Create aiohttp application."""
    webapp = web.Application()
    webapp.router.add_get('/sse', handle_sse)
    webapp.router.add_post('/messages', handle_messages)

    # Health check endpoint
    async def health(request):
        return web.json_response({"status": "healthy", "service": "monarch-money-mcp"})

    webapp.router.add_get('/health', health)

    return webapp

if __name__ == '__main__':
    print("Starting Monarch Money MCP HTTP Server on http://127.0.0.1:8100")
    print("SSE endpoint: http://127.0.0.1:8100/sse")
    print("Health check: http://127.0.0.1:8100/health")
    web.run_app(create_app(), host='127.0.0.1', port=8100)
