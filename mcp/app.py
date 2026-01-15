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
import signal
import json
import atexit
from pathlib import Path
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
from mcp.data_server import DataServer
from mcp.cache_server import CacheServer
from mcp.utility_server import UtilityServer
from mcp.background_loop import get_background_loop

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

# Initialize background event loop for long-running tasks
background_loop = get_background_loop()
logger.info("Background event loop initialized")

# Initialize MCP servers
mcp_server = UnifiedMCPServer()
data_server = DataServer()
cache_server = CacheServer()
utility_server = UtilityServer()

# Restore workflow state if backup exists
STATE_FILE = Path("/home/coolhand/shared/mcp/state_backup.json")
if STATE_FILE.exists():
    try:
        with STATE_FILE.open("r") as f:
            saved_state = json.load(f)
        mcp_server.workflow_state.load_state(saved_state)
        logger.info(
            "✓ Restored workflow state from %s (%d active, %d completed)",
            STATE_FILE,
            len(mcp_server.workflow_state.active_workflows),
            len(mcp_server.workflow_state.completed_workflows)
        )
    except Exception as exc:
        logger.error("Failed to restore workflow state from %s: %s", STATE_FILE, exc)

# Register streaming routes
register_streaming_routes(app, url_prefix='')

logger.info("Dreamwalker MCP Server initialized")
logger.info("Data Fetching Server initialized (Census, arXiv, Semantic Scholar, Archive)")
logger.info("Cache Server initialized (Redis)")
logger.info("Utility Server initialized (Document parsing, Multi-search, Citations)")


# -------------------------------------------------------------------------
# Root and Health Endpoints
# -------------------------------------------------------------------------

@app.route('/')
def index():
    """Root endpoint - server info."""
    return jsonify({
        'name': 'Dreamwalker MCP Server',
        'version': '2.0.0',
        'description': 'Dreamwalker orchestrator with comprehensive MCP tools for research, data fetching, caching, and utilities',
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
        'orchestrators': ['dreamwalker', 'beltalowda', 'swarm']
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    streaming_bridge = get_streaming_bridge()
    webhook_manager = get_webhook_manager()

    all_tools = []
    all_tools.extend(mcp_server.get_tools_manifest())
    all_tools.extend(data_server.get_tools_manifest())
    all_tools.extend(cache_server.get_tools_manifest())
    all_tools.extend(utility_server.get_tools_manifest())

    return jsonify({
        'status': 'healthy',
        'service': 'dreamwalker-mcp',
        'version': '2.0.0',
        'servers': {
            'orchestration': 'active',
            'data_fetching': 'active',
            'cache': 'active',
            'utilities': 'active'
        },
        'tool_count': len(all_tools),
        'active_streams': streaming_bridge.get_stats()['active_streams'],
        'registered_webhooks': webhook_manager.get_stats()['registered_webhooks']
    })


# -------------------------------------------------------------------------
# MCP Protocol Endpoints
# -------------------------------------------------------------------------

@app.route('/tools')
def list_tools():
    """List all available MCP tools."""
    tools = []
    tools.extend(mcp_server.get_tools_manifest())
    tools.extend(data_server.get_tools_manifest())
    tools.extend(cache_server.get_tools_manifest())
    tools.extend(utility_server.get_tools_manifest())
    return jsonify({
        'tools': tools,
        'count': len(tools)
    })


@app.route('/resources')
def list_resources():
    """List all available MCP resources."""
    resources = []
    resources.extend(mcp_server.get_resources_manifest())
    resources.extend(data_server.get_resources_manifest())
    resources.extend(cache_server.get_resources_manifest())
    resources.extend(utility_server.get_resources_manifest())
    return jsonify({
        'resources': resources,
        'count': len(resources)
    })


# -------------------------------------------------------------------------
# MCP Tool Execution Endpoints
# -------------------------------------------------------------------------

@app.route('/tools/orchestrate_research', methods=['POST'])
def orchestrate_research():
    """Execute Beltalowda hierarchical research workflow."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be valid JSON'
            }), 400

        # Run async function in background loop
        result = background_loop.run_sync(
            mcp_server.tool_dream_orchestrate_research(data),
            timeout=10.0  # Just wait for the task to be created, not completed
        )
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in orchestrate_research: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500


@app.route('/tools/orchestrate_search', methods=['POST'])
def orchestrate_search():
    """Execute Swarm multi-agent search workflow."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be valid JSON'
            }), 400

        # Run async function in background loop
        result = background_loop.run_sync(
            mcp_server.tool_dream_orchestrate_search(data),
            timeout=10.0  # Just wait for the task to be created, not completed
        )
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in orchestrate_search: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500


@app.route('/tools/get_orchestration_status', methods=['POST'])
def get_orchestration_status():
    """Get status of a running or completed orchestration."""
    try:
        data = request.get_json()
        result = background_loop.run_sync(
            mcp_server.tool_dream_get_orchestration_status(data),
            timeout=5.0
        )
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in get_orchestration_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/cancel_orchestration', methods=['POST'])
def cancel_orchestration():
    """Cancel a running orchestration."""
    try:
        data = request.get_json()
        result = background_loop.run_sync(
            mcp_server.tool_dream_cancel_orchestration(data),
            timeout=5.0
        )
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in cancel_orchestration: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/list_orchestrator_patterns', methods=['POST', 'GET'])
def list_orchestrator_patterns():
    """List available orchestrator patterns."""
    try:
        result = background_loop.run_sync(
            mcp_server.tool_dream_list_orchestrator_patterns({}),
            timeout=5.0
        )
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in list_orchestrator_patterns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/list_registered_tools', methods=['POST', 'GET'])
def list_registered_tools():
    """List tools registered in the tool registry."""
    try:
        data = request.get_json() if request.method == 'POST' else {}
        result = background_loop.run_sync(
            mcp_server.tool_dream_list_registered_tools(data),
            timeout=5.0
        )
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in list_registered_tools: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/execute_registered_tool', methods=['POST'])
def execute_registered_tool():
    """Execute a tool registered in the tool registry."""
    try:
        data = request.get_json()
        result = background_loop.run_sync(
            mcp_server.tool_dream_execute_registered_tool(data),
            timeout=10.0
        )
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in execute_registered_tool: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Data Fetching Tool Endpoints
# -------------------------------------------------------------------------

@app.route('/tools/fetch_census_acs', methods=['POST'])
def fetch_census_acs():
    """Fetch American Community Survey data."""
    try:
        data = request.get_json()
        result = data_server.tool_fetch_census_acs(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in fetch_census_acs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/fetch_census_saipe', methods=['POST'])
def fetch_census_saipe():
    """Fetch Small Area Income and Poverty Estimates."""
    try:
        data = request.get_json()
        result = data_server.tool_fetch_census_saipe(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in fetch_census_saipe: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/list_census_variables', methods=['POST'])
def list_census_variables():
    """Search Census variable catalog."""
    try:
        data = request.get_json() or {}
        result = data_server.tool_list_census_variables(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in list_census_variables: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/search_arxiv', methods=['POST'])
def search_arxiv():
    """Search arXiv for academic papers."""
    try:
        data = request.get_json()
        result = data_server.tool_search_arxiv(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in search_arxiv: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/search_semantic_scholar', methods=['POST'])
def search_semantic_scholar():
    """Search Semantic Scholar for research papers."""
    try:
        data = request.get_json()
        result = data_server.tool_search_semantic_scholar(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in search_semantic_scholar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/get_semantic_scholar_paper', methods=['POST'])
def get_semantic_scholar_paper():
    """Get detailed information about a specific paper."""
    try:
        data = request.get_json()
        result = data_server.tool_get_semantic_scholar_paper(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in get_semantic_scholar_paper: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/wayback_search', methods=['POST'])
def wayback_search():
    """Get the most recent archived snapshot of a URL."""
    try:
        data = request.get_json()
        result = data_server.tool_wayback_search(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in wayback_search: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/wayback_available_snapshots', methods=['POST'])
def wayback_available_snapshots():
    """List all available snapshots for a URL."""
    try:
        data = request.get_json()
        result = data_server.tool_wayback_available_snapshots(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in wayback_available_snapshots: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Cache Tool Endpoints
# -------------------------------------------------------------------------

@app.route('/tools/cache_get', methods=['POST'])
def cache_get():
    """Retrieve cached value."""
    try:
        data = request.get_json()
        result = cache_server.tool_cache_get(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in cache_get: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/cache_set', methods=['POST'])
def cache_set():
    """Store value with optional TTL."""
    try:
        data = request.get_json()
        result = cache_server.tool_cache_set(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in cache_set: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/cache_delete', methods=['POST'])
def cache_delete():
    """Delete key from cache."""
    try:
        data = request.get_json()
        result = cache_server.tool_cache_delete(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in cache_delete: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/cache_increment', methods=['POST'])
def cache_increment():
    """Increment counter."""
    try:
        data = request.get_json()
        result = cache_server.tool_cache_increment(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in cache_increment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/cache_exists', methods=['POST'])
def cache_exists():
    """Check if key exists."""
    try:
        data = request.get_json()
        result = cache_server.tool_cache_exists(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in cache_exists: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/cache_expire', methods=['POST'])
def cache_expire():
    """Set TTL on existing key."""
    try:
        data = request.get_json()
        result = cache_server.tool_cache_expire(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in cache_expire: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/cache_list_keys', methods=['POST'])
def cache_list_keys():
    """List keys matching pattern."""
    try:
        data = request.get_json() or {}
        result = cache_server.tool_cache_list_keys(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in cache_list_keys: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Utility Tool Endpoints
# -------------------------------------------------------------------------

@app.route('/tools/parse_document', methods=['POST'])
def parse_document():
    """Parse document (auto-detect format)."""
    try:
        data = request.get_json()
        result = utility_server.tool_parse_document(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in parse_document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/multi_provider_search', methods=['POST'])
def multi_provider_search():
    """Execute multi-query research workflow."""
    try:
        data = request.get_json()
        result = utility_server.tool_multi_provider_search(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in multi_provider_search: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/extract_citations', methods=['POST'])
def extract_citations():
    """Extract and format citations from text."""
    try:
        data = request.get_json()
        result = utility_server.tool_extract_citations(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in extract_citations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tools/format_citation_bibtex', methods=['POST'])
def format_citation_bibtex():
    """Format citation as BibTeX."""
    try:
        data = request.get_json()
        result = utility_server.tool_format_citation_bibtex(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in format_citation_bibtex: {e}")
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
# Graceful Shutdown Handling
# -------------------------------------------------------------------------

def save_state_on_shutdown():
    """Save workflow state to disk before exit."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state_data = mcp_server.workflow_state.serialize_state()

        with STATE_FILE.open("w") as f:
            json.dump(state_data, f, indent=2)

        logger.info(
            "✓ State saved to %s (%d active, %d completed)",
            STATE_FILE,
            len(state_data.get("active_workflows", {})),
            len(state_data.get("completed_workflows", {}))
        )

    except Exception as e:
        logger.error("Failed to save state: %s", e)

# Register shutdown handler


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    save_state_on_shutdown()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
atexit.register(save_state_on_shutdown)


# -------------------------------------------------------------------------
# Main Entry Point
# -------------------------------------------------------------------------

if __name__ == '__main__':
    # Get port from environment or default
    port = int(os.environ.get('PORT', 5060))

    # Start cleanup loop for streaming bridge
    streaming_bridge = get_streaming_bridge()

    logger.info(f"Starting Dreamwalker MCP Server on port {port}")
    logger.info("=" * 60)
    logger.info("🌊 Dreamwalker - Master Orchestrator")
    logger.info("=" * 60)
    logger.info("Available MCP Servers:")
    logger.info("  • Orchestration: Dreamwalker, Beltalowda, Swarm (7 tools)")
    logger.info("  • Data Fetching: Census, arXiv, Semantic Scholar, Archive (8 tools)")
    logger.info("  • Caching: Redis operations (7 tools)")
    logger.info("  • Utilities: Document parsing, Multi-search, Citations (4 tools)")
    logger.info(f"  Total: {len(mcp_server.get_tools_manifest()) + len(data_server.get_tools_manifest()) + len(cache_server.get_tools_manifest()) + len(utility_server.get_tools_manifest())} tools available")
    logger.info("=" * 60)
    logger.info(f"SSE streaming: GET /stream/{{task_id}}")
    logger.info(f"Webhooks: POST /webhook/register")

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('DEBUG', 'False').lower() == 'true'
    )
