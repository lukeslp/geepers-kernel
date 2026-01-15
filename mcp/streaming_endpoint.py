"""
SSE Streaming Endpoint for MCP Orchestrator

Flask blueprint providing Server-Sent Events endpoint for real-time
orchestrator progress updates.

Usage:
    from flask import Flask
    from shared.mcp import create_streaming_blueprint

    app = Flask(__name__)
    app.register_blueprint(create_streaming_blueprint(), url_prefix='/mcp')

    # Clients connect to: GET /mcp/stream/{task_id}
    # Events: new_post, stats_update, keepalive

Author: Luke Steuber
"""

import json
import logging
from flask import Blueprint, Response, stream_with_context, request, jsonify
from typing import Optional, Any

from .streaming import get_streaming_bridge, get_webhook_manager

logger = logging.getLogger(__name__)


def create_streaming_blueprint(
    blueprint_name: str = 'mcp_streaming',
    url_prefix: Optional[str] = None
) -> Blueprint:
    """
    Create Flask blueprint for SSE streaming endpoints.

    Args:
        blueprint_name: Blueprint name (default: mcp_streaming)
        url_prefix: URL prefix (optional, can be set during registration)

    Returns:
        Flask Blueprint

    Example:
        from flask import Flask
        from shared.mcp import create_streaming_blueprint

        app = Flask(__name__)
        bp = create_streaming_blueprint()
        app.register_blueprint(bp, url_prefix='/mcp')
    """
    bp = Blueprint(blueprint_name, __name__, url_prefix=url_prefix)

    streaming_bridge = get_streaming_bridge()
    webhook_manager = get_webhook_manager()

    # -------------------------------------------------------------------------
    # SSE Streaming Endpoint
    # -------------------------------------------------------------------------

    @bp.route('/stream/<task_id>')
    async def stream_orchestration(task_id: str):
        """
        SSE endpoint for real-time orchestration progress.

        Streams events from orchestrator workflow to client using
        Server-Sent Events (SSE) format.

        Args:
            task_id: Task identifier

        Query Parameters:
            timeout (int): Keepalive timeout in seconds (default: 30)

        Returns:
            SSE stream (text/event-stream)

        Event Types:
            - task_decomposed: Task broken into subtasks
            - agent_start: Agent started processing subtask
            - agent_complete: Agent completed subtask
            - synthesis_start: Synthesis phase started
            - synthesis_complete: Synthesis phase completed
            - workflow_complete: Workflow finished
            - workflow_error: Error occurred
            - keepalive: Periodic keepalive ping

        Example:
            # JavaScript client
            const eventSource = new EventSource('/mcp/stream/research_abc123');
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log(data.event_type, data.data);
            };
        """
        # Get timeout from query params
        timeout = request.args.get('timeout', type=int, default=30)

        async def generate():
            """Generate SSE events from streaming bridge."""
            try:
                # Check if stream exists
                queue = await streaming_bridge.get_stream(task_id)
                if not queue:
                    # Stream doesn't exist yet - create it and wait
                    logger.info(f"Creating new stream for task {task_id}")
                    queue = await streaming_bridge.create_stream(task_id)

                # Consume events and format as SSE
                async for event in streaming_bridge.consume_stream(task_id, timeout=timeout):
                    # Format as SSE
                    event_json = json.dumps(event)
                    yield f"data: {event_json}\n\n"

                # Stream ended - send final message
                yield f"data: {json.dumps({'event_type': 'stream_closed', 'task_id': task_id})}\n\n"

            except Exception as e:
                logger.exception(f"Error streaming task {task_id}: {e}")
                error_event = {
                    'event_type': 'stream_error',
                    'task_id': task_id,
                    'error': str(e)
                }
                yield f"data: {json.dumps(error_event)}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',  # Disable buffering in nginx
                'Connection': 'keep-alive'
            }
        )

    # -------------------------------------------------------------------------
    # Webhook Management Endpoints
    # -------------------------------------------------------------------------

    @bp.route('/webhook/register', methods=['POST'])
    def register_webhook():
        """
        Register webhook URL for task notifications.

        POST /mcp/webhook/register
        {
            "task_id": "research_abc123",
            "webhook_url": "https://example.com/webhook"
        }

        Returns:
            {success: bool, task_id: str}
        """
        try:
            data = request.get_json()
            task_id = data.get('task_id')
            webhook_url = data.get('webhook_url')

            if not task_id or not webhook_url:
                return jsonify({
                    'success': False,
                    'error': 'Missing task_id or webhook_url'
                }), 400

            webhook_manager.register_webhook(task_id, webhook_url)

            return jsonify({
                'success': True,
                'task_id': task_id,
                'webhook_url': webhook_url
            })

        except Exception as e:
            logger.exception(f"Error registering webhook: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @bp.route('/webhook/unregister', methods=['POST'])
    def unregister_webhook():
        """
        Unregister webhook for a task.

        POST /mcp/webhook/unregister
        {
            "task_id": "research_abc123"
        }

        Returns:
            {success: bool, task_id: str}
        """
        try:
            data = request.get_json()
            task_id = data.get('task_id')

            if not task_id:
                return jsonify({
                    'success': False,
                    'error': 'Missing task_id'
                }), 400

            webhook_manager.unregister_webhook(task_id)

            return jsonify({
                'success': True,
                'task_id': task_id
            })

        except Exception as e:
            logger.exception(f"Error unregistering webhook: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # -------------------------------------------------------------------------
    # Status and Stats Endpoints
    # -------------------------------------------------------------------------

    @bp.route('/stats')
    def streaming_stats():
        """
        Get streaming bridge and webhook manager statistics.

        GET /mcp/stats

        Returns:
            {
                streaming: {active_streams: int, ...},
                webhooks: {registered_webhooks: int, ...}
            }
        """
        try:
            return jsonify({
                'streaming': streaming_bridge.get_stats(),
                'webhooks': webhook_manager.get_stats()
            })

        except Exception as e:
            logger.exception(f"Error getting stats: {e}")
            return jsonify({
                'error': str(e)
            }), 500

    @bp.route('/health')
    def health_check():
        """
        Health check endpoint.

        GET /mcp/health

        Returns:
            {status: ok, active_streams: int}
        """
        try:
            stats = streaming_bridge.get_stats()
            return jsonify({
                'status': 'ok',
                'active_streams': stats['active_streams'],
                'timestamp': stats.get('timestamp')
            })

        except Exception as e:
            logger.exception(f"Health check failed: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    return bp


def register_streaming_routes(app: Any, url_prefix: str = '/mcp') -> None:
    """
    Convenience function to register streaming blueprint with Flask app.

    Args:
        app: Flask application instance
        url_prefix: URL prefix for streaming routes (default: /mcp)

    Example:
        from flask import Flask
        from shared.mcp import register_streaming_routes

        app = Flask(__name__)
        register_streaming_routes(app, url_prefix='/mcp')
    """
    bp = create_streaming_blueprint()
    app.register_blueprint(bp, url_prefix=url_prefix)
    logger.info(f"Registered MCP streaming routes at {url_prefix}")


# -------------------------------------------------------------------------
# Standalone SSE Example (for testing)
# -------------------------------------------------------------------------

if __name__ == '__main__':
    """
    Standalone SSE server for testing.

    Run with: python -m shared.mcp.streaming_endpoint
    """
    from flask import Flask

    app = Flask(__name__)
    register_streaming_routes(app, url_prefix='/mcp')

    @app.route('/')
    def index():
        """Test page with SSE client."""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>MCP Streaming Test</title>
    <style>
        body { font-family: monospace; padding: 20px; }
        #events { background: #f0f0f0; padding: 10px; height: 400px; overflow-y: scroll; }
        .event { margin: 5px 0; padding: 5px; background: white; }
        .error { background: #ffcccc; }
        .success { background: #ccffcc; }
    </style>
</head>
<body>
    <h1>MCP Streaming Test</h1>
    <div>
        <label>Task ID: <input type="text" id="taskId" value="test_123" /></label>
        <button onclick="connect()">Connect</button>
        <button onclick="disconnect()">Disconnect</button>
    </div>
    <h2>Events:</h2>
    <div id="events"></div>

    <script>
        let eventSource = null;

        function connect() {
            const taskId = document.getElementById('taskId').value;
            if (eventSource) {
                eventSource.close();
            }

            eventSource = new EventSource('/mcp/stream/' + taskId);

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                addEvent(data, 'success');
            };

            eventSource.onerror = (error) => {
                addEvent({error: 'Connection error'}, 'error');
                console.error('SSE error:', error);
            };

            addEvent({status: 'Connected to ' + taskId}, 'success');
        }

        function disconnect() {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
                addEvent({status: 'Disconnected'}, 'success');
            }
        }

        function addEvent(data, className = '') {
            const eventsDiv = document.getElementById('events');
            const eventDiv = document.createElement('div');
            eventDiv.className = 'event ' + className;
            eventDiv.textContent = new Date().toISOString() + ' - ' + JSON.stringify(data, null, 2);
            eventsDiv.insertBefore(eventDiv, eventsDiv.firstChild);
        }
    </script>
</body>
</html>
        '''

    print("Starting MCP streaming test server on http://localhost:5555")
    print("Open browser to http://localhost:5555 to test SSE streaming")
    app.run(host='0.0.0.0', port=5555, debug=True)
