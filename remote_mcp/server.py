"""
Remote MCP Server (Streamable HTTP)

FastMCP wrapper exposing Dreamwalker orchestrator tools over streamable HTTP
for Claude Desktop Custom Connectors.

Delegates all tool calls to the existing UnifiedMCPServer class.
Secured with bearer token auth via Starlette middleware.

Port: 5061
Caddy route: https://dr.eamer.dev/mcp-remote/

Author: Luke Steuber
"""

import os
import sys
import logging
import importlib.util
from typing import Optional, List, Dict, Any

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# ---------------------------------------------------------------------------
# Import fastmcp FIRST while sys.path is clean (no ~/shared shadowing PyPI mcp)
# ---------------------------------------------------------------------------
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Save reference to PyPI mcp modules (loaded by fastmcp)
_pypi_mcp_modules = {
    k: v for k, v in sys.modules.items()
    if k == 'mcp' or k.startswith('mcp.')
}

# ---------------------------------------------------------------------------
# Now add ~/shared to path and load our local modules.
# Temporarily remove PyPI mcp from sys.modules so Python finds our local one.
# ---------------------------------------------------------------------------

# Remove PyPI mcp temporarily so `from mcp.xxx` finds our local package
for k in list(_pypi_mcp_modules):
    sys.modules.pop(k, None)

from shared.config import ConfigManager
from shared.mcp.unified_server import UnifiedMCPServer

# Restore PyPI mcp modules so fastmcp continues to work at runtime
sys.modules.update(_pypi_mcp_modules)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bearer token auth middleware
# ---------------------------------------------------------------------------

AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN")
if not AUTH_TOKEN:
    raise RuntimeError("MCP_AUTH_TOKEN environment variable is required")


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid Bearer token."""

    async def dispatch(self, request: Request, call_next):
        # Allow health checks unauthenticated
        if request.url.path == "/health":
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401,
            )

        token = auth_header[len("Bearer "):]
        if token != AUTH_TOKEN:
            return JSONResponse(
                {"error": "Invalid bearer token"},
                status_code=401,
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Shared UnifiedMCPServer instance
# ---------------------------------------------------------------------------

_config = ConfigManager(app_name='remote_mcp')
_server = UnifiedMCPServer(config_manager=_config)

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp_server = FastMCP(
    "Dreamwalker",
    version="1.0.0",
    instructions=(
        "Dreamwalker orchestrator tools for multi-agent research and search. "
        "Use dream_orchestrate_research for hierarchical research workflows "
        "and dream_orchestrate_search for multi-domain parallel search."
    ),
)


# -- Tools -----------------------------------------------------------------

@mcp_server.tool()
async def dream_orchestrate_research(
    task: str,
    title: Optional[str] = None,
    num_agents: int = 8,
    enable_drummer: bool = True,
    enable_camina: bool = True,
    generate_documents: bool = True,
    document_formats: Optional[List[str]] = None,
    provider_name: str = "xai",
    model: Optional[str] = None,
    budget_tier: str = "balanced",
    webhook_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute Dream Cascade hierarchical research workflow with three-tier synthesis."""
    return await _server.tool_dream_orchestrate_research({
        "task": task,
        "title": title,
        "num_agents": num_agents,
        "enable_drummer": enable_drummer,
        "enable_camina": enable_camina,
        "generate_documents": generate_documents,
        "document_formats": document_formats or ["markdown"],
        "provider_name": provider_name,
        "model": model,
        "budget_tier": budget_tier,
        "webhook_url": webhook_url,
    })


@mcp_server.tool()
async def dream_orchestrate_search(
    query: str,
    title: Optional[str] = None,
    num_agents: int = 5,
    allowed_agent_types: Optional[List[str]] = None,
    generate_documents: bool = True,
    document_formats: Optional[List[str]] = None,
    provider_name: str = "xai",
    model: Optional[str] = None,
    budget_tier: str = "balanced",
    webhook_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute Dream Swarm multi-agent search workflow with specialized agent types."""
    return await _server.tool_dream_orchestrate_search({
        "query": query,
        "title": title,
        "num_agents": num_agents,
        "allowed_agent_types": allowed_agent_types,
        "generate_documents": generate_documents,
        "document_formats": document_formats or ["markdown"],
        "provider_name": provider_name,
        "model": model,
        "budget_tier": budget_tier,
        "webhook_url": webhook_url,
    })


@mcp_server.tool()
async def dreamwalker_status(task_id: str) -> Dict[str, Any]:
    """Get status of a running or completed orchestration."""
    return await _server.tool_dreamwalker_status({"task_id": task_id})


@mcp_server.tool()
async def dreamwalker_cancel(task_id: str) -> Dict[str, Any]:
    """Cancel a running orchestration."""
    return await _server.tool_dreamwalker_cancel({"task_id": task_id})


@mcp_server.tool()
async def dreamwalker_patterns() -> Dict[str, Any]:
    """List available orchestrator patterns (Dream Cascade, Dream Swarm, etc.)."""
    return await _server.tool_dreamwalker_patterns({})


@mcp_server.tool()
async def dreamwalker_list_tools(
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """List tools registered in the tool registry."""
    return await _server.tool_dreamwalker_list_tools({
        "category": category,
        "tags": tags,
    })


@mcp_server.tool()
async def dreamwalker_execute_tool(
    tool_name: str,
    tool_arguments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a tool registered in the tool registry."""
    return await _server.tool_dreamwalker_execute_tool({
        "tool_name": tool_name,
        "tool_arguments": tool_arguments or {},
    })


# ---------------------------------------------------------------------------
# ASGI app for uvicorn
# ---------------------------------------------------------------------------

app = mcp_server.http_app(
    path="/",
    transport="streamable-http",
    middleware=[Middleware(BearerAuthMiddleware)],
)
