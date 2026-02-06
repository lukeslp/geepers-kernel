#!/bin/bash
cd /home/coolhand/shared/remote_mcp
set -a; source .env; set +a

# Unset PYTHONPATH to prevent ~/shared/mcp from shadowing PyPI mcp package.
# The server.py manages sys.path internally to load both packages correctly.
unset PYTHONPATH

exec /home/coolhand/shared/mcp/remote-venv/bin/uvicorn server:app --host 127.0.0.1 --port 5061
