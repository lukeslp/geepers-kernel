#!/usr/bin/env python3
"""
MCP Orchestrator Server

Production Flask application serving the Unified MCP Server with
SSE streaming support for orchestrator workflows.

Deployment:
    # Development
    python app.py

    # Production (Gunicorn)
    gunicorn -w 4 -b 0.0.0.0:5060 --timeout 300 app:app

    # Via service manager
    sm start mcp-server

Routes:
    GET  /              - Health check and server info
    GET  /health        - Health check endpoint
    GET  /tools         - List available MCP tools
    GET  /resources     - List available MCP resources

    # Orchestrator Tools (POST with JSON body)
    POST /tools/orchestrate_research
    POST /tools/orchestrate_search
    POST /tools/get_orchestration_status
    POST /tools/cancel_orchestration
    POST /tools/list_orchestrator_patterns
    POST /tools/list_registered_tools
    POST /tools/execute_registered_tool

    # Streaming
    GET  /stream/{task_id}          - SSE stream for workflow progress
    POST /webhook/register          - Register webhook for task
    POST /webhook/unregister        - Unregister webhook
    GET  /stats                     - Streaming bridge stats

Author: Luke Steuber
"""

import os
import sys
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add shared to path
sys.path.insert(0, '/home/coolhand/shared')

from mcp import (
    UnifiedMCPServer,
    register_streaming_routes,
    get_streaming_bridge,
    get_webhook_manager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Enable CORS for web clients
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:*", "https://dr.eamer.dev", "https://d.reamwalker.com", "https://d.reamwalk.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Initialize MCP server
mcp_server = UnifiedMCPServer()

# Register streaming routes
register_streaming_routes(app, url_prefix='')

logger.info("MCP Orchestrator Server initialized")


# -------------------------------------------------------------------------
# Root and Health Endpoints
# -------------------------------------------------------------------------

@app.route('/')
def index():
    """Root endpoint - server info."""
    return jsonify({
        'name': 'MCP Orchestrator Server',
        'version': '1.0.0',
        'description': 'Unified MCP server for orchestrator agents with SSE streaming',
        'author': 'Luke Steuber',
        'endpoints': {
            'health': '/health',
            'tools': '/tools',
            'resources': '/resources',
            'orchestrate_research': '/tools/orchestrate_research',
            'orchestrate_search': '/tools/orchestrate_search',
            'stream': '/stream/{task_id}',
            'webhook_register': '/webhook/register',
            'stats': '/stats'
        },
        'orchestrators': ['beltalowda', 'swarm']
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    streaming_bridge = get_streaming_bridge()
    webhook_manager = get_webhook_manager()

    return jsonify({
        'status': 'healthy',
        'service': 'mcp-orchestrator',
        'active_streams': streaming_bridge.get_stats()['active_streams'],
        'registered_webhooks': webhook_manager.get_stats()['registered_webhooks']
    })


# -------------------------------------------------------------------------
# MCP Protocol Endpoints
# -------------------------------------------------------------------------

@app.route('/tools')
def list_tools():
    """List all available MCP tools."""
    tools = mcp_server.get_tools_manifest()
    return jsonify({
        'tools': tools,
        'count': len(tools)
    })


@app.route('/resources')
def list_resources():
    """List all available MCP resources."""
    resources = mcp_server.get_resources_manifest()
    return jsonify({
        'resources': resources,
        'count': len(resources)
    })


# -------------------------------------------------------------------------
# MCP Tool Execution Endpoints
# -------------------------------------------------------------------------

@app.route('/tools/orchestrate_research', methods=['POST'])
async def orchestrate_research():
    """Execute Beltalowda hierarchical research workflow."""
    try:
        data = request.get_json()
        result = await mcp_server.tool_orchestrate_research(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in orchestrate_research: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/orchestrate_search', methods=['POST'])
async def orchestrate_search():
    """Execute Swarm multi-agent search workflow."""
    try:
        data = request.get_json()
        result = await mcp_server.tool_orchestrate_search(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in orchestrate_search: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/get_orchestration_status', methods=['POST'])
async def get_orchestration_status():
    """Get status of a running or completed orchestration."""
    try:
        data = request.get_json()
        result = await mcp_server.tool_get_orchestration_status(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in get_orchestration_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/cancel_orchestration', methods=['POST'])
async def cancel_orchestration():
    """Cancel a running orchestration."""
    try:
        data = request.get_json()
        result = await mcp_server.tool_cancel_orchestration(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in cancel_orchestration: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/list_orchestrator_patterns', methods=['POST', 'GET'])
async def list_orchestrator_patterns():
    """List available orchestrator patterns."""
    try:
        result = await mcp_server.tool_list_orchestrator_patterns({})
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in list_orchestrator_patterns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/list_registered_tools', methods=['POST', 'GET'])
async def list_registered_tools():
    """List tools registered in the tool registry."""
    try:
        data = request.get_json() if request.method == 'POST' else {}
        result = await mcp_server.tool_list_registered_tools(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in list_registered_tools: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/execute_registered_tool', methods=['POST'])
async def execute_registered_tool():
    """Execute a tool registered in the tool registry."""
    try:
        data = request.get_json()
        result = await mcp_server.tool_execute_registered_tool(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in execute_registered_tool: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Error Handlers
# -------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': {
            'health': '/health',
            'tools': '/tools',
            'resources': '/resources'
        }
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.exception(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': str(error)
    }), 500


# -------------------------------------------------------------------------
# Main Entry Point
# -------------------------------------------------------------------------

if __name__ == '__main__':
    # Get port from environment or default
    port = int(os.environ.get('PORT', 5060))

    # Start cleanup loop for streaming bridge
    import asyncio
    streaming_bridge = get_streaming_bridge()

    logger.info(f"Starting MCP Orchestrator Server on port {port}")
    logger.info("Available orchestrators: Beltalowda (hierarchical research), Swarm (multi-agent search)")
    logger.info(f"SSE streaming: GET /stream/{{task_id}}")
    logger.info(f"Webhooks: POST /webhook/register")

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('DEBUG', 'False').lower() == 'true'
    )
