#!/bin/bash
cd /home/coolhand/shared/remote_mcp
set -a; source .env; set +a
exec /home/coolhand/shared/mcp/remote-venv/bin/uvicorn server:app --host 127.0.0.1 --port 5061
