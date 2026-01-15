# Monarch Money MCP Server Setup

This MCP server exposes your Monarch Money financial data to Claude Code (CLI and Desktop).

## Installation

1. **Install MCP SDK** (already done):
   ```bash
   pip install mcp>=0.9.0
   ```

2. **Add to Claude Code Configuration**:

   Edit `~/.claude.json` and add to the `mcpServers` section under your project:

   ```json
   {
     "projects": {
       "/home/coolhand": {
         "mcpServers": {
           "monarch-money": {
             "type": "stdio",
             "command": "python3",
             "args": [
               "/home/coolhand/tools/monarchmoney/mcp_server/server.py"
             ],
             "env": {}
           }
         }
       }
     }
   }
   ```

   **OR** use the launcher script:

   ```json
   {
     "projects": {
       "/home/coolhand": {
         "mcpServers": {
           "monarch-money": {
             "type": "stdio",
             "command": "/home/coolhand/tools/monarchmoney/mcp_server/run.sh",
             "args": [],
             "env": {}
           }
         }
       }
     }
   }
   ```

3. **Restart Claude Code** to load the new MCP server.

## Available Tools

Once configured, Claude will have access to these tools:

### Financial Query Tools

1. **`get_accounts`** - Get all accounts with balances and status
   - No parameters required
   - Returns: List of accounts with name, type, balance, status

2. **`get_transactions`** - Get recent transactions
   - Parameters:
     - `limit` (number, optional): Max transactions (default: 50, max: 500)
     - `start_date` (string, optional): Start date (YYYY-MM-DD)
     - `end_date` (string, optional): End date (YYYY-MM-DD)
     - `search` (string, optional): Search term for merchant/description
   - Returns: List of transactions with date, merchant, amount, category

3. **`get_budgets`** - Get budget information
   - No parameters required
   - Returns: Budget status by category with budgeted, spent, remaining

4. **`get_cashflow`** - Get cashflow summary
   - Parameters:
     - `start_date` (string, optional): Start date (default: 30 days ago)
     - `end_date` (string, optional): End date (default: today)
   - Returns: Income, expenses, savings summary

5. **`search_transactions`** - Search transactions
   - Parameters:
     - `query` (string, required): Search query
     - `limit` (number, optional): Max results (default: 20)
   - Returns: Matching transactions

6. **`get_spending_summary`** - Get spending by category
   - Parameters:
     - `start_date` (string, optional): Start date (default: 30 days ago)
     - `end_date` (string, optional): End date (default: today)
   - Returns: Spending totals by category

7. **`get_net_worth`** - Get current net worth
   - No parameters required
   - Returns: Net worth, assets, liabilities

## Usage Examples

Once configured, you can ask Claude:

```
"What's my current net worth?"
"Show me my transactions from last month"
"What did I spend on groceries this month?"
"Am I over budget in any categories?"
"What are my top 5 spending categories?"
```

Claude will automatically use the appropriate MCP tools to fetch the data.

## Authentication

The MCP server uses your saved encrypted session from the CLI tool. Make sure you've logged in at least once:

```bash
mm login
```

The server will automatically use the encrypted session stored in `~/.mm/`.

## Logging

Server logs are written to `~/.mm/logs/` along with CLI logs.

## Troubleshooting

### Server not starting

Check Claude Code logs for errors. You can also test the server manually:

```bash
cd /home/coolhand/tools/monarchmoney
python3 -m mcp_server.server
```

### Authentication errors

Re-login using the CLI:

```bash
mm login
```

### Tools not appearing

Make sure:
1. The configuration is in the correct place in `~/.claude.json`
2. You've restarted Claude Code after adding the configuration
3. The `mcpServers` section is properly formatted JSON

## Security

- Session tokens are encrypted at rest using Fernet
- MCP server runs locally, no external network access
- Only accessible to Claude Code on your machine
- Uses the same secure session storage as the CLI tool

## Integration with Other MCP Servers

This server works alongside other MCP servers you may have configured:
- playwright (browser automation)
- serena (IDE assistant)
- orchestrator (Dream Cascade/Swarm)
- claude-in-chrome (browser control)

All tools are namespaced, so there are no conflicts.
