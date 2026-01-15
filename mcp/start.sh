#!/bin/bash
# MCP Orchestrator Server Startup Script
# Author: Luke Steuber

set -e

# Change to script directory
cd "$(dirname "$0")"

# Load environment variables from parent .env if it exists
if [ -f "/home/coolhand/.env" ]; then
    echo "Loading environment from /home/coolhand/.env"
    set -a
    source /home/coolhand/.env
    set +a
fi

# Default configuration
PORT="${PORT:-5060}"
WORKERS="${WORKERS:-4}"
TIMEOUT="${TIMEOUT:-300}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment (system site packages enabled)..."
    python3 -m venv --system-site-packages venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies (optional)
if [ "${SKIP_PIP_INSTALL:-0}" = "1" ]; then
    echo "Skipping dependency installation (SKIP_PIP_INSTALL=1)"
else
    echo "Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
fi

# Start server with Gunicorn using async workers
echo "Starting MCP Orchestrator Server on port $PORT with $WORKERS async workers"
echo "Timeout: ${TIMEOUT}s (for long-running orchestrations)"

exec gunicorn \
    -w "$WORKERS" \
    -k gevent \
    -b "127.0.0.1:$PORT" \
    --timeout "$TIMEOUT" \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    app:app
