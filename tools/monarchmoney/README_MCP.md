# Monarch Money MCP Integration

This directory contains a complete MCP (Model Context Protocol) server implementation for Monarch Money, enabling Claude to directly query your financial data.

## What You Get

**7 MCP Tools** that let Claude access your Monarch Money data:
- `get_accounts` - All accounts with balances
- `get_transactions` - Recent transactions with filters
- `get_budgets` - Budget status by category
- `get_cashflow` - Income/expense summary
- `search_transactions` - Search by merchant/category
- `get_spending_summary` - Spending by category
- `get_net_worth` - Current net worth calculation

## Usage Modes

### Mode 1: Claude Code CLI (stdio) - ✅ Already Configured

**What**: MCP server runs as subprocess when you use Claude Code CLI
**When**: Daily work in terminal
**Setup**: Already done! Configuration in `~/.claude.json`

Just ask Claude:
```
"What's my net worth?"
"Show transactions from last week"
"Am I over budget?"
```

### Mode 2: Claude Desktop (stdio) - Local Machine

**What**: Same as Mode 1, but for Claude Desktop app
**When**: You prefer GUI over CLI
**Setup**: 2 minutes

1. Find config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add this configuration:
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

3. Restart Claude Desktop

**Docs**: `MCP_DESKTOP_SETUP.md` (Option 1)

### Mode 3: HTTP Server - Remote Access

**What**: Run MCP server as HTTP service for remote access
**When**: Using Claude Desktop on different machine, or want persistent server
**Setup**: 5 minutes

```bash
# Start server
cd /home/coolhand/tools/monarchmoney
./mcp_server/manage.sh start

# Configure Claude Desktop (any machine)
# Use http://localhost:8100/sse as the endpoint
```

**Docs**: `HTTP_SERVER_QUICKSTART.md`

### Mode 4: Systemd Service - Always Running

**What**: HTTP server as system service, starts on boot
**When**: Production deployment, always-on access
**Setup**: 5 minutes

```bash
# Install service
sudo cp monarch-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable monarch-mcp
sudo systemctl start monarch-mcp

# Check status
sudo systemctl status monarch-mcp
```

**Docs**: `HTTP_SERVER_QUICKSTART.md` (Systemd section)

### Mode 5: SSH Tunnel - Secure Remote

**What**: SSH tunnel from remote machine to local HTTP server
**When**: Access from laptop while server runs on dr.eamer.dev
**Setup**: 1 minute

```bash
# On your laptop
ssh -L 8100:localhost:8100 coolhand@dr.eamer.dev

# Keep terminal open, configure Claude Desktop to use localhost:8100
```

**Docs**: `MCP_DESKTOP_SETUP.md` (Option 4)

### Mode 6: Caddy HTTPS - Production

**What**: HTTPS reverse proxy with authentication
**When**: Internet-accessible endpoint with security
**Setup**: 10 minutes (requires Caddy)

Add to Caddyfile:
```
finance.dr.eamer.dev {
    reverse_proxy localhost:8100
    basicauth {
        coolhand $2a$14$HASHED_PASSWORD
    }
}
```

**Docs**: `MCP_DESKTOP_SETUP.md` (Option 5)

## Quick Reference

| Mode | Use Case | Complexity | Security |
|------|----------|------------|----------|
| Claude Code CLI | Daily terminal work | ✅ Zero (done) | 🔒 Highest |
| Claude Desktop Local | GUI preference | ⚡ 2 min | 🔒 Highest |
| HTTP Server | Remote access | ⚡ 5 min | 🔒 High (localhost) |
| Systemd Service | Always-on server | ⚡ 5 min | 🔒 High (localhost) |
| SSH Tunnel | Secure remote | ⚡ 1 min | 🔒 Highest |
| Caddy HTTPS | Internet access | 🔧 10 min | 🔒 High (with auth) |

## Files in This Directory

```
monarchmoney/
├── mcp_server/
│   ├── __init__.py           # Package marker
│   ├── server.py             # Main MCP server (stdio)
│   ├── http_server.py        # HTTP/SSE wrapper
│   ├── manage.sh             # HTTP server management
│   └── run.sh                # Simple launcher
│
├── monarch-mcp.service       # Systemd service config
│
├── README_MCP.md             # This file (overview)
├── MCP_SETUP.md              # Technical setup guide
├── MCP_README.md             # User guide with examples
├── MCP_DESKTOP_SETUP.md      # Claude Desktop + remote options
└── HTTP_SERVER_QUICKSTART.md # HTTP server quick start
```

## Example Queries

Once configured, ask Claude these kinds of questions:

**Balance & Net Worth**:
- "What's my current net worth?"
- "Show me all my account balances"
- "How much cash do I have?"

**Transactions**:
- "What did I spend at Amazon last month?"
- "Show my recent transactions"
- "Find all Starbucks purchases this year"

**Budgets**:
- "Am I over budget anywhere?"
- "What's my grocery budget status?"
- "Show me all budget categories"

**Analysis**:
- "What are my top 5 spending categories?"
- "Calculate my monthly savings rate"
- "Show income vs expenses for last quarter"

## Authentication

All modes use your encrypted session from the CLI tool:

```bash
# Login once (creates encrypted session)
mm login

# Session stored in ~/.mm/session.enc (encrypted)
# All MCP modes reuse this session
```

## Troubleshooting

### "MCP server not found"
- Check config file location (varies by OS)
- Verify Python path is correct
- Restart Claude Code/Desktop

### "Authentication failed"
- Run `mm login` to refresh session
- Check `~/.mm/session.enc` exists
- Verify file permissions (should be 0600)

### "Connection refused" (HTTP mode)
- Check server is running: `./mcp_server/manage.sh status`
- Test health: `curl http://localhost:8100/health`
- Check logs: `./mcp_server/manage.sh logs`

### "Tools not appearing in Claude"
- Make sure you're in correct project directory
- Restart Claude completely (not just reload)
- Check `~/.claude.json` has monarch-money server

## Security Best Practices

### For Local Use (Modes 1-2)
- ✅ Most secure (no network exposure)
- ✅ Session encrypted at rest
- ✅ No additional setup needed

### For HTTP Server (Modes 3-4)
- ✅ Bind to localhost (127.0.0.1) only
- ✅ Never expose port 8100 to internet
- ✅ Use SSH tunnel for remote access

### For Production (Mode 6)
- ✅ Always use HTTPS (not HTTP)
- ✅ Enable HTTP Basic Auth minimum
- ✅ Consider rate limiting
- ✅ Rotate credentials regularly
- ⚠️ Don't commit credentials to git

## Next Steps

**Just starting?** Use Mode 1 (Claude Code CLI) - it's already configured!

**Want GUI?** Set up Mode 2 (Claude Desktop Local) - 2 minute config

**Need remote access?** Try Mode 5 (SSH Tunnel) - most secure remote option

**Production deployment?** Mode 6 (Caddy HTTPS) with proper authentication

## Documentation

- **Quick Start**: `MCP_README.md`
- **Technical Details**: `MCP_SETUP.md`
- **Claude Desktop**: `MCP_DESKTOP_SETUP.md`
- **HTTP Server**: `HTTP_SERVER_QUICKSTART.md`

## Support

All modes use the same underlying:
- Monarch Money GraphQL API
- Encrypted session storage
- Same 7 MCP tools

Choose the mode that fits your workflow!
