# Monarch Money MCP for Claude Desktop

This guide shows how to use the Monarch Money MCP server with **Claude Desktop** and other remote Claude applications.

## Option 1: Claude Desktop (Local stdio)

Claude Desktop can connect to local MCP servers via stdio just like Claude Code CLI.

### Setup for Claude Desktop

1. **Find Claude Desktop config file**:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Add Monarch Money MCP server**:

```json
{
  "mcpServers": {
    "monarch-money": {
      "command": "python3",
      "args": [
        "/home/coolhand/tools/monarchmoney/mcp_server/server.py"
      ]
    }
  }
}
```

3. **Restart Claude Desktop**

4. **Verify** - Look for "🔌" icon in Claude Desktop showing available tools

## Option 2: Remote MCP Server (HTTP/SSE)

For remote access (from Claude Desktop on another machine, or web-based Claude), you can run the MCP server as an HTTP service.

### Create HTTP Server Wrapper

Create `/home/coolhand/tools/monarchmoney/mcp_server/http_server.py`:

```python
#!/usr/bin/env python3
"""
HTTP/SSE wrapper for Monarch Money MCP Server.
Allows remote access from Claude Desktop or web clients.
"""

import asyncio
from aiohttp import web
from mcp.server.sse import sse_server
import sys

sys.path.insert(0, '/home/coolhand/tools/monarchmoney')
from mcp_server.server import app

async def handle_sse(request):
    \"\"\"Handle SSE connection for MCP.\"\"\"
    async with sse_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

async def handle_messages(request):
    \"\"\"Handle MCP messages over HTTP POST.\"\"\"
    # Handle incoming MCP messages
    return web.Response(text="OK")

async def create_app():
    \"\"\"Create aiohttp application.\"\"\"
    app = web.Application()
    app.router.add_get('/sse', handle_sse)
    app.router.add_post('/messages', handle_messages)
    return app

if __name__ == '__main__':
    web.run_app(create_app(), host='127.0.0.1', port=8100)
```

### Run HTTP Server

```bash
cd /home/coolhand/tools/monarchmoney
python3 mcp_server/http_server.py
```

### Configure Claude Desktop for HTTP

In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "monarch-money": {
      "url": "http://127.0.0.1:8100/sse"
    }
  }
}
```

## Option 3: Systemd Service (Always Running)

For a persistent MCP server that starts on boot:

### Create Service File

`/etc/systemd/system/monarch-mcp.service`:

```ini
[Unit]
Description=Monarch Money MCP Server
After=network.target

[Service]
Type=simple
User=coolhand
WorkingDirectory=/home/coolhand/tools/monarchmoney
ExecStart=/usr/bin/python3 /home/coolhand/tools/monarchmoney/mcp_server/http_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable monarch-mcp
sudo systemctl start monarch-mcp
sudo systemctl status monarch-mcp
```

Now the MCP server runs continuously and Claude Desktop can connect to it.

## Option 4: SSH Tunnel (Remote Machine)

If you want to access from Claude Desktop on a **different machine**:

### On Server (dr.eamer.dev)

Run MCP server:
```bash
python3 /home/coolhand/tools/monarchmoney/mcp_server/http_server.py
```

### On Client Machine

Create SSH tunnel:
```bash
ssh -L 8100:localhost:8100 coolhand@dr.eamer.dev
```

### Configure Claude Desktop (on client)

```json
{
  "mcpServers": {
    "monarch-money": {
      "url": "http://localhost:8100/sse"
    }
  }
}
```

Now Claude Desktop on your laptop can access Monarch Money data on your server!

## Option 5: Caddy Reverse Proxy (HTTPS)

For secure remote access with authentication:

### Add to Caddyfile

```
finance.dr.eamer.dev {
    reverse_proxy localhost:8100

    basicauth {
        coolhand $2a$14$YOUR_HASHED_PASSWORD
    }
}
```

### Configure Claude Desktop

```json
{
  "mcpServers": {
    "monarch-money": {
      "url": "https://finance.dr.eamer.dev/sse",
      "headers": {
        "Authorization": "Basic <base64-encoded-credentials>"
      }
    }
  }
}
```

## Security Considerations

### Local stdio (Option 1)
- ✓ Most secure - no network exposure
- ✓ Uses encrypted session files
- ✓ Only accessible from local machine

### HTTP/SSE (Options 2-4)
- ⚠️ Binds to localhost by default
- ⚠️ Add authentication for remote access
- ⚠️ Use HTTPS for internet exposure
- ⚠️ Consider firewall rules

### Recommended Setup

**For single machine**: Use Option 1 (stdio)
**For home network**: Use Option 2 (HTTP) with localhost binding
**For remote access**: Use Option 5 (Caddy with HTTPS + auth)

## Testing

Test the MCP server with curl:

```bash
# Test stdio server
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | \
  python3 /home/coolhand/tools/monarchmoney/mcp_server/server.py

# Test HTTP server
curl http://localhost:8100/sse
```

## Troubleshooting

### "MCP server not found" in Claude Desktop

1. Check config file location (varies by OS)
2. Verify Python path is correct
3. Check server.py is executable
4. Restart Claude Desktop completely

### "Connection refused"

1. Check HTTP server is running: `lsof -i :8100`
2. Verify firewall allows port 8100
3. Check logs for errors

### "Authentication failed"

1. Verify you've run `mm login` at least once
2. Check `~/.mm/session.enc` and `~/.mm/session.key` exist
3. Ensure file permissions (should be 0600)

## Benefits of Each Approach

| Approach | Pros | Cons |
|----------|------|------|
| stdio (1) | Simplest, most secure | Local only |
| HTTP (2) | Remote capable | Needs auth for security |
| Systemd (3) | Always available | Uses system resources |
| SSH Tunnel (4) | Secure remote | Requires SSH access |
| Caddy (5) | Production-grade | Most complex setup |

## Recommended: Start with stdio

For most users, **Option 1 (stdio)** is best:
- Simple configuration
- Works out of the box
- Most secure
- No additional services needed

Upgrade to HTTP/SSE only if you need:
- Remote access from other machines
- Multiple Claude instances
- Always-on availability
- Web-based Claude interfaces

## Current Status

Your Monarch Money MCP server is currently configured for:
- ✓ Claude Code CLI (stdio) - Active
- ✓ Ready for Claude Desktop (stdio) - Add config
- ⚠️ HTTP/SSE - Requires http_server.py creation

Choose the approach that fits your use case!
