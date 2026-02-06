"""
Remote MCP Server (Streamable HTTP)

FastMCP wrapper exposing Dreamwalker orchestrator tools over streamable HTTP
for Claude Desktop Custom Connectors.

Delegates all tool calls to the existing UnifiedMCPServer class.
Secured with bearer token auth via Starlette middleware.

Port: 5061
Caddy route: https://dr.eamer.dev/mcp/

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
# Import fastmcp FIRST (needs PyPI `mcp` package from venv site-packages).
# We must NOT have ~/shared on sys.path yet, or `mcp` resolves to our local
# ~/shared/mcp/ package instead of the PyPI one.
# ---------------------------------------------------------------------------
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ---------------------------------------------------------------------------
# Now load our local modules. We add ~/shared to path for transitive deps
# (orchestration, llm_providers, config, etc.). To avoid colliding with
# the PyPI `mcp` already in sys.modules, we load our local mcp package
# under the name `dreamwalker_mcp` using importlib.
# ---------------------------------------------------------------------------
sys.path.insert(0, '/home/coolhand/shared')

from config import ConfigManager

# Load our local mcp package under a non-colliding name
_mcp_init = os.path.join('/home/coolhand/shared/mcp', '__init__.py')
_mcp_spec = importlib.util.spec_from_file_location(
    'dreamwalker_mcp', _mcp_init,
    submodule_search_locations=['/home/coolhand/shared/mcp']
)
_dmcp = importlib.util.module_from_spec(_mcp_spec)
sys.modules['dreamwalker_mcp'] = _dmcp
_mcp_spec.loader.exec_module(_dmcp)

# Load unified_server as a submodule
_us_spec = importlib.util.spec_from_file_location(
    'dreamwalker_mcp.unified_server',
    os.path.join('/home/coolhand/shared/mcp', 'unified_server.py')
)
_us_mod = importlib.util.module_from_spec(_us_spec)
sys.modules['dreamwalker_mcp.unified_server'] = _us_mod
_us_spec.loader.exec_module(_us_mod)

UnifiedMCPServer = _us_mod.UnifiedMCPServer

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
