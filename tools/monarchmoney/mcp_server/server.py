#!/usr/bin/env python3
"""
Monarch Money MCP Server

Provides MCP tools for querying financial data from Monarch Money.
Allows Claude to directly access accounts, transactions, budgets, and insights.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# MCP SDK imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Monarch Money imports
sys.path.insert(0, '/home/coolhand/shared/tools/monarchmoney')
from monarchmoney.monarchmoney import MonarchMoney
from monarchmoney.logger import logger

# Initialize MCP server
app = Server("monarch-money")

# Global MM instance (initialized on first use)
_mm_instance: Optional[MonarchMoney] = None


async def get_mm() -> MonarchMoney:
    """Get or create MonarchMoney instance with saved session."""
    global _mm_instance

    if _mm_instance is None:
        _mm_instance = MonarchMoney(use_secure_storage=True)
        try:
            await _mm_instance.login(use_saved_session=True)
            logger.info("MCP Server: Logged in using saved session")
        except Exception as e:
            logger.error(f"MCP Server: Failed to login: {e}")
            raise

    return _mm_instance


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Monarch Money tools."""
    return [
        Tool(
            name="get_accounts",
            description="Get all Monarch Money accounts with balances and status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_transactions",
            description="Get recent transactions with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of transactions to return (default: 50, max: 500)",
                        "default": 50
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (optional)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional)",
                    },
                    "search": {
                        "type": "string",
                        "description": "Search term to filter by merchant or description (optional)",
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_budgets",
            description="Get budget information and spending status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_cashflow",
            description="Get cashflow summary (income, expenses, savings)",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional, defaults to today)",
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="search_transactions",
            description="Search transactions by merchant, category, or description",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (merchant name, category, or description)",
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (default: 20)",
                        "default": 20
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_spending_summary",
            description="Get spending summary by category for a date range",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional, defaults to today)",
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_net_worth",
            description="Get current net worth (assets minus liabilities)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls from Claude."""
    try:
        mm = await get_mm()

        if name == "get_accounts":
            accounts_data = await mm.get_accounts()
            accounts = accounts_data.get('accounts', [])

            # Format for readability
            result = []
            for acc in accounts:
                result.append({
                    "name": acc.get('displayName'),
                    "type": acc.get('type', {}).get('display'),
                    "balance": acc.get('currentBalance', 0),
                    "status": "Disabled" if acc.get('syncDisabled') else "Active",
                    "hidden": acc.get('isHidden', False),
                    "includeInNetWorth": acc.get('includeInNetWorth', True)
                })

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "get_transactions":
            limit = arguments.get('limit', 50)
            start_date = arguments.get('start_date')
            end_date = arguments.get('end_date')
            search = arguments.get('search')

            # Build filter params
            filter_params = {'limit': min(limit, 500)}
            if start_date:
                filter_params['start_date'] = start_date
            if end_date:
                filter_params['end_date'] = end_date

            transactions_data = await mm.get_transactions(**filter_params)
            transactions = transactions_data.get('allTransactions', {}).get('results', [])

            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                transactions = [
                    t for t in transactions
                    if search_lower in t.get('merchant', {}).get('name', '').lower() or
                       search_lower in (t.get('notes') or '').lower()
                ]

            # Format for readability
            result = []
            for t in transactions[:limit]:
                result.append({
                    "date": t.get('date'),
                    "merchant": t.get('merchant', {}).get('name', 'Unknown'),
                    "amount": t.get('amount', 0),
                    "category": t.get('category', {}).get('name'),
                    "account": t.get('account', {}).get('displayName'),
                    "notes": t.get('notes'),
                    "pending": t.get('pending', False)
                })

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "get_budgets":
            budgets_data = await mm.get_budgets()
            budgets = budgets_data.get('budgets', [])

            # Format for readability
            result = []
            for b in budgets:
                result.append({
                    "category": b.get('category', {}).get('name'),
                    "budgeted": b.get('amount', 0),
                    "spent": b.get('spent', 0),
                    "remaining": b.get('amount', 0) - b.get('spent', 0),
                    "percentage": (b.get('spent', 0) / b.get('amount', 1)) * 100 if b.get('amount') else 0
                })

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "get_cashflow":
            start_date = arguments.get('start_date')
            end_date = arguments.get('end_date')

            # Default to last 30 days
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')

            cashflow_data = await mm.get_cashflow_summary(start_date, end_date)

            return [TextContent(
                type="text",
                text=json.dumps(cashflow_data, indent=2)
            )]

        elif name == "search_transactions":
            query = arguments.get('query', '')
            limit = arguments.get('limit', 20)

            # Get recent transactions and filter
            transactions_data = await mm.get_transactions(limit=500)
            transactions = transactions_data.get('allTransactions', {}).get('results', [])

            query_lower = query.lower()
            results = []
            for t in transactions:
                if (query_lower in t.get('merchant', {}).get('name', '').lower() or
                    query_lower in (t.get('category', {}).get('name') or '').lower() or
                    query_lower in (t.get('notes') or '').lower()):
                    results.append({
                        "date": t.get('date'),
                        "merchant": t.get('merchant', {}).get('name', 'Unknown'),
                        "amount": t.get('amount', 0),
                        "category": t.get('category', {}).get('name'),
                        "notes": t.get('notes')
                    })

                    if len(results) >= limit:
                        break

            return [TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )]

        elif name == "get_spending_summary":
            start_date = arguments.get('start_date')
            end_date = arguments.get('end_date')

            # Default to last 30 days
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')

            # Get transactions
            transactions_data = await mm.get_transactions(
                start_date=start_date,
                end_date=end_date,
                limit=500
            )
            transactions = transactions_data.get('allTransactions', {}).get('results', [])

            # Summarize by category
            category_totals = {}
            for t in transactions:
                if t.get('amount', 0) < 0:  # Expenses only
                    category = t.get('category', {}).get('name', 'Uncategorized')
                    category_totals[category] = category_totals.get(category, 0) + abs(t.get('amount', 0))

            # Sort by amount
            result = [
                {"category": cat, "total": amt}
                for cat, amt in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            ]

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "get_net_worth":
            accounts_data = await mm.get_accounts()
            accounts = accounts_data.get('accounts', [])

            total = 0
            assets = 0
            liabilities = 0

            for acc in accounts:
                if not acc.get('isHidden') and acc.get('includeInNetWorth', True):
                    balance = acc.get('currentBalance', 0)
                    total += balance

                    if acc.get('isAsset', True):
                        assets += balance
                    else:
                        liabilities += abs(balance)

            result = {
                "net_worth": total,
                "total_assets": assets,
                "total_liabilities": liabilities,
                "as_of": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        logger.error(f"MCP Server: Tool call failed: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    logger.info("Starting Monarch Money MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
