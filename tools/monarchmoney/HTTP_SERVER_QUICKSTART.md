# Monarch Money MCP HTTP Server - Quick Start

The HTTP server enables remote access to your Monarch Money data from Claude Desktop or other Claude instances.

## Quick Start (Local Machine)

### 1. Start the HTTP Server

```bash
cd /home/coolhand/tools/monarchmoney
./mcp_server/manage.sh start
```

Output:
```
🚀 Starting Monarch Money MCP HTTP Server...
✅ Server started on http://127.0.0.1:8100 (PID: 12345)
   SSE endpoint: http://127.0.0.1:8100/sse
   Health check: http://127.0.0.1:8100/health
   Logs: /home/coolhand/.mm/logs/mcp_http.log
```

### 2. Test the Server

```bash
./mcp_server/manage.sh test
```

### 3. Configure Claude Desktop

Edit your Claude Desktop config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Add:
```json
{
  "mcpServers": {
    "monarch-money": {
      "url": "http://localhost:8100/sse"
    }
  }
}
```

### 4. Restart Claude Desktop

Close and reopen Claude Desktop. Look for the 🔌 icon showing available MCP tools.

### 5. Try It!

Ask Claude Desktop:
```
"What's my current net worth?"
"Show me my recent transactions"
"Am I over budget anywhere?"
```

## Management Commands

```bash
# Start server
./mcp_server/manage.sh start

# Stop server
./mcp_server/manage.sh stop

# Restart server
./mcp_server/manage.sh restart

# Check status
./mcp_server/manage.sh status

# View logs
./mcp_server/manage.sh logs

# Test endpoints
./mcp_server/manage.sh test
```

## Run as Systemd Service (Always On)

### Install Service

```bash
# Copy service file
sudo cp /home/coolhand/tools/monarchmoney/monarch-mcp.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable monarch-mcp
sudo systemctl start monarch-mcp

# Check status
sudo systemctl status monarch-mcp
```

### Manage Service

```bash
# Start
sudo systemctl start monarch-mcp

# Stop
sudo systemctl stop monarch-mcp

# Restart
sudo systemctl restart monarch-mcp

# View logs
sudo journalctl -u monarch-mcp -f
```

## Remote Access (Different Machine)

### Option A: SSH Tunnel (Recommended)

On your **client machine** (where Claude Desktop is):

```bash
# Create SSH tunnel
ssh -L 8100:localhost:8100 coolhand@dr.eamer.dev

# Keep this terminal open
```

Then configure Claude Desktop with:
```json
{
  "mcpServers": {
    "monarch-money": {
      "url": "http://localhost:8100/sse"
    }
  }
}
```

### Option B: Caddy Reverse Proxy (Production)

On **dr.eamer.dev**, add to `/etc/caddy/Caddyfile`:

```
finance.dr.eamer.dev {
    reverse_proxy localhost:8100

    basicauth {
        coolhand $2a$14$YOUR_HASHED_PASSWORD
    }
}
```

Generate password hash:
```bash
caddy hash-password
```

Then configure Claude Desktop with:
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

## Troubleshooting

### Server won't start

Check if port 8100 is in use:
```bash
lsof -i :8100
```

Kill conflicting process or change port in `http_server.py`.

### Authentication errors

Re-login with CLI:
```bash
mm login
```

Verify session files exist:
```bash
ls -la ~/.mm/session.*
```

### Connection refused from Claude Desktop

1. Verify server is running: `./mcp_server/manage.sh status`
2. Test health endpoint: `curl http://localhost:8100/health`
3. Check logs: `./mcp_server/manage.sh logs`

### SSH tunnel issues

Make sure tunnel is active:
```bash
# On client machine
ps aux | grep "ssh.*8100"
```

Re-establish tunnel if needed.

## Security Notes

### Local HTTP Server (127.0.0.1)
- ✅ Only accessible from local machine
- ✅ Uses encrypted session tokens
- ✅ No network exposure

### SSH Tunnel
- ✅ Encrypted SSH connection
- ✅ Port forwarding secure
- ✅ Requires SSH authentication

### Caddy with HTTPS
- ✅ TLS encryption
- ✅ HTTP Basic Auth
- ✅ Rate limiting possible
- ⚠️ Credentials in config (use environment variables instead)

## What's Next?

1. **Test locally**: Start server, configure Claude Desktop, test queries
2. **Optional**: Set up systemd service for always-on availability
3. **Optional**: Configure SSH tunnel for remote access
4. **Optional**: Deploy Caddy reverse proxy for production HTTPS

The HTTP server provides the foundation for all remote access scenarios!
