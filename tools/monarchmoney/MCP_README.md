# Monarch Money MCP Integration

## What This Does

Your Monarch Money CLI is now integrated with Claude Code via MCP (Model Context Protocol). This means Claude can **directly query your financial data** during conversations without you needing to manually run commands.

## Quick Start

### 1. The MCP Server is Already Configured ✓

The server is automatically available when you're in the `/home/coolhand` project.

### 2. Restart Claude Code

Close and reopen Claude Code for the MCP server to load.

### 3. Try It Out!

Ask Claude questions like:

```
"What's my current net worth?"
"Show me my transactions from last month"
"What did I spend on Amazon this month?"
"Am I over budget anywhere?"
"What are my top 5 spending categories?"
```

Claude will automatically use MCP tools to fetch the data!

## Available Tools

Claude now has these tools available:

| Tool | What It Does |
|------|--------------|
| `get_accounts` | Get all accounts with balances |
| `get_transactions` | Get recent transactions (with filters) |
| `get_budgets` | Get budget status by category |
| `get_cashflow` | Get income/expense summary |
| `search_transactions` | Search by merchant/category |
| `get_spending_summary` | Spending totals by category |
| `get_net_worth` | Current net worth calculation |

## How It Works

1. **You ask Claude** a question about finances
2. **Claude determines** which MCP tool(s) to use
3. **MCP server** fetches data from Monarch Money API
4. **Claude analyzes** the data and responds

All using your encrypted session from `mm login`!

## Examples

### Example 1: Quick Balance Check
```
User: "What's my net worth?"

Claude: [Uses get_net_worth tool]
"Your current net worth is $X,XXX. This includes:
- Total assets: $X,XXX
- Total liabilities: $X,XXX

As of January 6, 2026"
```

### Example 2: Transaction Analysis
```
User: "What did I spend on groceries in December?"

Claude: [Uses search_transactions with query="grocery"]
"You spent $X,XXX on groceries in December across these transactions:
- Whole Foods: $XX
- Trader Joe's: $XX
..."
```

### Example 3: Budget Check
```
User: "Am I over budget anywhere?"

Claude: [Uses get_budgets tool]
"You're over budget in 2 categories:
- Dining: $XXX spent of $XXX budgeted (120%)
- Entertainment: $XXX spent of $XXX budgeted (105%)

Still within budget:
- Groceries: $XXX of $XXX (85%)
..."
```

## Security

- ✓ Uses encrypted session tokens (same as CLI)
- ✓ Runs locally on your machine only
- ✓ No external network access beyond Monarch Money API
- ✓ Session stored securely in `~/.mm/`

## Troubleshooting

### "I don't see the tools in Claude"

1. Make sure you're in the `/home/coolhand` project
2. Restart Claude Code completely
3. Check `~/.claude.json` has the `monarch-money` server listed

### "Authentication error"

Re-login using the CLI:
```bash
mm login
```

### "Tools not working"

Check the MCP server is running:
```bash
python3 /home/coolhand/tools/monarchmoney/mcp_server/server.py
```

Should start without errors (press Ctrl+C to stop).

## CLI vs MCP

| Feature | CLI (`mm`) | MCP Server |
|---------|------------|------------|
| Use case | Manual commands | Claude conversations |
| Interface | Terminal | Claude Code |
| Authentication | Encrypted session | Same session |
| Tools available | All commands | 7 core queries |
| Output | Rich tables | JSON for Claude |

Both use the same underlying Monarch Money API and encrypted sessions.

## Integration with Other Features

The MCP server works alongside:
- ✓ `mm` CLI commands (use both!)
- ✓ Other MCP servers (playwright, serena, etc.)
- ✓ Claude Code features (git, tasks, agents)

No conflicts - they're all complementary!

## Files

```
monarchmoney/
├── mcp_server/
│   ├── __init__.py
│   ├── server.py         # Main MCP server
│   └── run.sh            # Launcher script
├── MCP_README.md         # This file
└── MCP_SETUP.md          # Technical setup guide
```

## Next Steps

1. **Restart Claude Code** to load the MCP server
2. **Try a query** like "What's my net worth?"
3. **Watch Claude** automatically use the MCP tools
4. **Ask follow-ups** - Claude has full context!

Enjoy having Claude as your AI financial assistant with direct access to your data!
