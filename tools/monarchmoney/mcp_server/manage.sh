#!/bin/bash
# Monarch Money MCP Server Management Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
HTTP_SERVER="$SCRIPT_DIR/http_server.py"
PID_FILE="$HOME/.mm/mcp_http.pid"

command=$1

case "$command" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "❌ MCP HTTP server is already running (PID: $(cat "$PID_FILE"))"
            exit 1
        fi

        echo "🚀 Starting Monarch Money MCP HTTP Server..."
        cd "$PROJECT_DIR"
        nohup python3 "$HTTP_SERVER" > "$HOME/.mm/logs/mcp_http.log" 2>&1 &
        echo $! > "$PID_FILE"
        echo "✅ Server started on http://127.0.0.1:8100 (PID: $!)"
        echo "   SSE endpoint: http://127.0.0.1:8100/sse"
        echo "   Health check: http://127.0.0.1:8100/health"
        echo "   Logs: $HOME/.mm/logs/mcp_http.log"
        ;;

    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "❌ No PID file found. Server may not be running."
            exit 1
        fi

        PID=$(cat "$PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            echo "🛑 Stopping MCP HTTP server (PID: $PID)..."
            kill $PID
            rm "$PID_FILE"
            echo "✅ Server stopped"
        else
            echo "❌ Server not running (stale PID file removed)"
            rm "$PID_FILE"
        fi
        ;;

    restart)
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            PID=$(cat "$PID_FILE")
            echo "✅ MCP HTTP server is running (PID: $PID)"
            echo "   Endpoint: http://127.0.0.1:8100/sse"

            # Test health endpoint
            if curl -s http://127.0.0.1:8100/health > /dev/null 2>&1; then
                echo "   Health: OK"
            else
                echo "   Health: ⚠️  Unreachable"
            fi
        else
            echo "❌ MCP HTTP server is not running"
            [ -f "$PID_FILE" ] && rm "$PID_FILE"
        fi
        ;;

    logs)
        if [ -f "$HOME/.mm/logs/mcp_http.log" ]; then
            tail -f "$HOME/.mm/logs/mcp_http.log"
        else
            echo "❌ No log file found at $HOME/.mm/logs/mcp_http.log"
        fi
        ;;

    test)
        echo "🧪 Testing MCP HTTP server..."

        # Check if server is running
        if ! curl -s http://127.0.0.1:8100/health > /dev/null 2>&1; then
            echo "❌ Server not responding. Make sure it's running with: $0 start"
            exit 1
        fi

        # Test health endpoint
        echo "Testing health endpoint..."
        HEALTH=$(curl -s http://127.0.0.1:8100/health)
        echo "✅ Health check: $HEALTH"

        echo ""
        echo "✅ All tests passed!"
        echo "   Your MCP server is ready for Claude Desktop"
        ;;

    *)
        echo "Monarch Money MCP Server Management"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|test}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the MCP HTTP server"
        echo "  stop     - Stop the MCP HTTP server"
        echo "  restart  - Restart the MCP HTTP server"
        echo "  status   - Check if server is running"
        echo "  logs     - Tail server logs"
        echo "  test     - Test server endpoints"
        exit 1
        ;;
esac
