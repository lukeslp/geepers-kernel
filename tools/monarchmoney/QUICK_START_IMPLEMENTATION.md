# Quick Start Implementation Guide
**Created**: 2026-01-05

## Overview
This guide provides the fastest path to implementing CLI + LLM enhancements for monarchmoney.

## Prerequisites
```bash
cd /home/coolhand/tools/monarchmoney
git checkout -b feature/cli-llm-enhancement
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install click rich anthropic openai pydantic tenacity structlog
```

## Step 1: Create Exception Hierarchy (30 min)

Create `monarchmoney/exceptions.py`:
```python
"""Exception hierarchy for MonarchMoney library."""

class MonarchMoneyError(Exception):
    """Base exception for all MonarchMoney errors."""
    pass

class AuthenticationError(MonarchMoneyError):
    """Authentication-related errors."""
    pass

class RequireMFAException(AuthenticationError):
    """Multi-factor authentication required."""
    pass

class LoginFailedException(AuthenticationError):
    """Login attempt failed."""
    pass

class ValidationError(MonarchMoneyError):
    """Input validation failed."""
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"{field}: {message}")

class APIError(MonarchMoneyError):
    """API request failed."""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)

class RequestFailedException(APIError):
    """API request failed."""
    pass

class NetworkError(MonarchMoneyError):
    """Network-related errors."""
    pass
```

Update imports in `monarchmoney.py`:
```python
from .exceptions import (
    MonarchMoneyError,
    AuthenticationError,
    RequireMFAException,
    LoginFailedException,
    ValidationError,
    APIError,
    RequestFailedException,
    NetworkError
)
```

## Step 2: Add Basic Logging (20 min)

Add to top of `monarchmoney.py`:
```python
import logging
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger(__name__)
```

Replace key `print()` statements:
```python
# Before:
print(f"Using saved session found at {self._session_file}")

# After:
logger.info("using_saved_session", session_file=self._session_file)
```

## Step 3: Create Basic CLI Structure (1 hour)

Create `monarchmoney/cli/main.py`:
```python
"""CLI entry point for MonarchMoney."""
import asyncio
import click
from rich.console import Console
from rich.table import Table
from monarchmoney import MonarchMoney

console = Console()

@click.group()
@click.version_option()
def cli():
    """MonarchMoney CLI - Manage your finances from the command line."""
    pass

@cli.command()
def login():
    """Login to your Monarch Money account."""
    email = click.prompt("Email")
    password = click.prompt("Password", hide_input=True)

    mm = MonarchMoney()

    async def do_login():
        try:
            await mm.login(email, password, use_saved_session=False)
            console.print("[green]✓ Logged in successfully![/green]")
        except Exception as e:
            console.print(f"[red]✗ Login failed: {e}[/red]")

    asyncio.run(do_login())

@cli.group()
def accounts():
    """Manage accounts."""
    pass

@accounts.command(name="list")
def accounts_list():
    """List all accounts."""
    mm = MonarchMoney()

    async def do_list():
        try:
            mm.load_session()
            data = await mm.get_accounts()

            table = Table(title="Accounts")
            table.add_column("Account", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Balance", style="green", justify="right")

            for account in data.get("accounts", []):
                table.add_row(
                    account["displayName"],
                    account["type"]["display"],
                    f"${account['currentBalance']:,.2f}"
                )

            console.print(table)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    asyncio.run(do_list())

if __name__ == "__main__":
    cli()
```

Add to `setup.py`:
```python
entry_points={
    'console_scripts': [
        'mm=monarchmoney.cli.main:cli',
    ],
},
```

Test:
```bash
python -m monarchmoney.cli.main --help
python -m monarchmoney.cli.main accounts list
```

## Step 4: Add LLM Integration (2 hours)

Create `monarchmoney/llm/agent.py`:
```python
"""LLM Agent for MonarchMoney."""
import sys
sys.path.insert(0, '/home/coolhand/shared')

from llm_providers.anthropic_provider import AnthropicProvider
from llm_providers import Message
from typing import List, Dict, Any, Optional
import json
from monarchmoney import MonarchMoney

class MonarchMoneyAgent:
    """LLM-powered financial assistant."""

    SYSTEM_PROMPT = """You are a helpful financial assistant with access to the user's Monarch Money account.

You can help with:
- Checking account balances
- Searching transactions
- Analyzing spending patterns
- Budget tracking
- Financial insights

Be conversational, supportive, and explain financial concepts simply.
Always provide specific numbers and dates when available.
Ask clarifying questions if needed.

Available tools:
- get_accounts: List all accounts and balances
- search_transactions: Search for specific transactions
- get_spending_summary: Analyze spending by category
"""

    def __init__(self, monarch: MonarchMoney, provider: str = "anthropic", model: str = None):
        self.monarch = monarch
        self.provider_name = provider

        if provider == "anthropic":
            from llm_providers.anthropic_provider import AnthropicProvider
            self.provider = AnthropicProvider()
            self.model = model or "claude-3-5-sonnet-20241022"
        elif provider == "openai":
            from llm_providers.openai_provider import OpenAIProvider
            self.provider = OpenAIProvider()
            self.model = model or "gpt-4-turbo-preview"
        else:
            raise ValueError(f"Unknown provider: {provider}")

        self.conversation_history: List[Message] = []
        self.tools = self._define_tools()

    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define tools available to the LLM."""
        return [
            {
                "name": "get_accounts",
                "description": "Get all accounts and their current balances",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                }
            },
            {
                "name": "search_transactions",
                "description": "Search for transactions by description, category, or amount",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of transactions to return (default 10)"
                        }
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool and return the result."""
        if tool_name == "get_accounts":
            data = await self.monarch.get_accounts()
            accounts = data.get("accounts", [])
            result = []
            for acc in accounts:
                result.append({
                    "name": acc["displayName"],
                    "type": acc["type"]["display"],
                    "balance": acc["currentBalance"]
                })
            return json.dumps(result, indent=2)

        elif tool_name == "search_transactions":
            limit = tool_input.get("limit", 10)
            data = await self.monarch.get_transactions(limit=limit)
            transactions = data.get("allTransactions", {}).get("results", [])
            result = []
            for txn in transactions:
                result.append({
                    "date": txn["date"],
                    "merchant": txn.get("merchant", {}).get("name", "Unknown"),
                    "amount": txn["amount"],
                    "category": txn.get("category", {}).get("name", "Uncategorized")
                })
            return json.dumps(result, indent=2)

        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    async def chat(self, message: str) -> str:
        """Chat with the financial assistant."""
        # Add user message to history
        self.conversation_history.append(Message(role="user", content=message))

        # Prepare messages with system prompt
        messages = [Message(role="system", content=self.SYSTEM_PROMPT)]
        messages.extend(self.conversation_history)

        # Get response from LLM
        response = self.provider.complete(
            messages,
            model=self.model,
            tools=self.tools if hasattr(self.provider, 'tools') else None
        )

        # Handle tool calls if any
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_results = []
            for tool_call in response.tool_calls:
                result = await self._execute_tool(
                    tool_call.name,
                    tool_call.input
                )
                tool_results.append(result)

            # Add tool results to conversation and get final response
            # (This is simplified - proper implementation needs tool result formatting)
            self.conversation_history.append(Message(
                role="assistant",
                content=f"Tool results: {tool_results}"
            ))

            messages.extend(self.conversation_history[-1:])
            response = self.provider.complete(messages, model=self.model)

        # Add assistant response to history
        self.conversation_history.append(Message(
            role="assistant",
            content=response.content
        ))

        return response.content
```

Add chat command to `cli/main.py`:
```python
@cli.command()
def chat():
    """Interactive chat with financial assistant."""
    from monarchmoney.llm.agent import MonarchMoneyAgent

    mm = MonarchMoney()
    mm.load_session()

    agent = MonarchMoneyAgent(mm)

    console.print("[bold cyan]MonarchMoney Assistant[/bold cyan]")
    console.print("Type 'exit' to quit\n")

    async def chat_loop():
        while True:
            user_input = console.input("[bold green]You:[/bold green] ")

            if user_input.lower() in ('exit', 'quit'):
                break

            response = await agent.chat(user_input)
            console.print(f"[bold blue]Assistant:[/bold blue] {response}\n")

    asyncio.run(chat_loop())

@cli.command()
@click.argument('question')
def ask(question):
    """Ask a one-off question about your finances."""
    from monarchmoney.llm.agent import MonarchMoneyAgent

    mm = MonarchMoney()
    mm.load_session()

    agent = MonarchMoneyAgent(mm)

    async def do_ask():
        response = await agent.chat(question)
        console.print(response)

    asyncio.run(do_ask())
```

## Step 5: Test Everything (30 min)

```bash
# Test CLI
python -m monarchmoney.cli.main --help
python -m monarchmoney.cli.main login
python -m monarchmoney.cli.main accounts list

# Test LLM (after login)
python -m monarchmoney.cli.main ask "What are my account balances?"
python -m monarchmoney.cli.main chat
```

## Step 6: Add pyproject.toml (15 min)

Create `pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "monarchmoney"
version = "0.2.0"
description = "Python library and CLI for Monarch Money API"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [
    {name = "hammem", email = "hammem@users.noreply.github.com"}
]
dependencies = [
    "aiohttp>=3.9.0,<4.0",
    "gql[aiohttp]>=3.4.0,<4.0",
    "oathtool>=2.3.0,<3.0",
    "graphql-core>=3.2.0,<4.0",
    "python-dotenv>=1.0.0,<2.0",
    "click>=8.1.0,<9.0",
    "rich>=13.0.0,<14.0",
    "structlog>=24.0.0,<25.0",
]

[project.optional-dependencies]
llm = [
    "anthropic>=0.18.0,<1.0",
    "openai>=1.12.0,<2.0",
]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
mm = "monarchmoney.cli.main:cli"

[tool.black]
line-length = 100
target-version = ['py38']

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## Checkpoint: Basic Working Version

At this point you should have:
- ✅ Exception hierarchy
- ✅ Basic logging
- ✅ CLI with login and accounts commands
- ✅ LLM agent with tool execution
- ✅ Chat and ask commands

Test everything:
```bash
mm --help
mm login
mm accounts list
mm ask "What are my accounts?"
mm chat
```

## Next Steps (Optional)

1. **Add more CLI commands**
   - `mm transactions list`
   - `mm budgets list`
   - `mm reports cashflow`

2. **Improve LLM tools**
   - Add more sophisticated tools
   - Better error handling
   - Context retention across sessions

3. **Refactor monarchmoney.py**
   - Split into modules (client.py, auth.py, queries/)
   - Move GraphQL queries to separate files

4. **Add tests**
   - Unit tests for new code
   - Integration tests for CLI
   - LLM tool tests

5. **Documentation**
   - Update README with CLI examples
   - Add LLM integration guide
   - Create beginner tutorials

## Common Issues

### Import Errors
```bash
# Make sure you're in the right directory
cd /home/coolhand/tools/monarchmoney

# Make sure package is installed in dev mode
pip install -e .
```

### LLM Provider Errors
```bash
# Check API keys
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Load from .env if needed
export $(cat /home/coolhand/.env | xargs)
```

### Async Errors
```python
# Always use asyncio.run() for top-level async calls
asyncio.run(mm.get_accounts())

# Not:
await mm.get_accounts()  # Only works inside async function
```

## Quick Commands

```bash
# Install in development mode
pip install -e .

# Run CLI
python -m monarchmoney.cli.main

# Or after install:
mm

# Run tests
pytest

# Format code
black monarchmoney/

# Lint
ruff check monarchmoney/

# Type check
mypy monarchmoney/
```

## Time Estimate Summary

| Task | Time |
|------|------|
| Step 1: Exceptions | 30 min |
| Step 2: Logging | 20 min |
| Step 3: Basic CLI | 1 hour |
| Step 4: LLM Integration | 2 hours |
| Step 5: Testing | 30 min |
| Step 6: pyproject.toml | 15 min |
| **Total MVP** | **4-5 hours** |

This gets you a working CLI with LLM integration. Full implementation (all commands, refactoring, comprehensive tests) will take 64-80 hours as outlined in the main roadmap.

---

**For full details, see**:
- `/home/coolhand/tools/monarchmoney/ENHANCEMENT_ROADMAP.md`
- `/home/coolhand/geepers/reports/by-date/2026-01-05/python-monarchmoney.md`
