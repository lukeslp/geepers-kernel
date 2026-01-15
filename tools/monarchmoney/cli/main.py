"""
Main CLI entry point for Monarch Money.

Provides a beautiful command-line interface for managing finances with LLM-powered insights.
"""

import asyncio
import click
from rich.console import Console
from rich.table import Table

from monarchmoney.logger import logger
from cli.commands.transactions import transactions
from cli.commands.budgets import budgets
from cli.commands.insights import insights
from cli.commands.chat import chat

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="mm")
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, verbose):
    """
    Monarch Money CLI - Manage your finances with AI assistance.

    A command-line tool for interacting with Monarch Money, featuring natural language
    queries, budget analysis, and LLM-powered financial insights.
    """
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose

    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")
        logger.info("CLI started in verbose mode")


@cli.command()
@click.pass_context
def login(ctx):
    """Interactive login to Monarch Money."""
    console.print("[bold green]Monarch Money Login[/bold green]")
    console.print("Please enter your credentials:")

    email = click.prompt('Email')
    password = click.prompt('Password', hide_input=True)

    async def do_login():
        from monarchmoney.monarchmoney import MonarchMoney
        mm = MonarchMoney(use_secure_storage=True)

        try:
            await mm.login(email, password, use_saved_session=False, save_session=True)
            console.print("[bold green]✓[/bold green] Login successful!")
            logger.info(f"User logged in: {email}")

        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Login failed: {str(e)}")
            logger.error(f"Login failed for {email}: {str(e)}")
            raise click.Abort()

    asyncio.run(do_login())


@cli.command()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.pass_context
def accounts(ctx, output_json):
    """List all accounts."""
    async def list_accounts():
        from monarchmoney.monarchmoney import MonarchMoney
        mm = MonarchMoney(use_secure_storage=True)

        try:
            await mm.login(use_saved_session=True)
            accounts_data = await mm.get_accounts()

            if output_json:
                import json
                console.print_json(json.dumps(accounts_data, indent=2))
            else:
                table = Table(title="Your Accounts")
                table.add_column("Name", style="cyan")
                table.add_column("Type", style="magenta")
                table.add_column("Balance", justify="right", style="green")
                table.add_column("Status", style="yellow")

                for account in accounts_data.get('accounts', []):
                    balance = account.get('currentBalance', 0)
                    table.add_row(
                        account.get('displayName', 'Unknown'),
                        account.get('type', {}).get('display', 'Unknown'),
                        f"${balance:,.2f}",
                        account.get('syncDisabled') and "Disabled" or "Active"
                    )

                console.print(table)
                logger.info(f"Listed {len(accounts_data.get('accounts', []))} accounts")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            logger.error(f"Failed to list accounts: {str(e)}")
            raise click.Abort()

    asyncio.run(list_accounts())


@cli.command()
@click.option('--no-cache', is_flag=True, help='Skip cache, fetch fresh data')
def balance(no_cache):
    """Quick balance check across all accounts."""
    async def get_balance():
        from monarchmoney.monarchmoney import MonarchMoney
        from cli.cache import get_cached, set_cached, is_cache_enabled

        try:
            # Try cache first (unless disabled or --no-cache flag)
            if not no_cache and is_cache_enabled():
                cached_accounts = get_cached('accounts', ttl_seconds=300)
                if cached_accounts:
                    accounts_data = cached_accounts
                else:
                    mm = MonarchMoney(use_secure_storage=True)
                    await mm.login(use_saved_session=True)
                    accounts_data = await mm.get_accounts()
                    set_cached('accounts', accounts_data)
            else:
                mm = MonarchMoney(use_secure_storage=True)
                await mm.login(use_saved_session=True)
                accounts_data = await mm.get_accounts()

            # Calculate totals
            total = 0
            asset_total = 0
            liability_total = 0

            for acc in accounts_data.get('accounts', []):
                if not acc.get('isHidden', False) and acc.get('includeInNetWorth', True):
                    balance = acc.get('currentBalance', 0)
                    total += balance

                    if acc.get('isAsset', True):
                        asset_total += balance
                    else:
                        liability_total += abs(balance)

            # Display results
            from rich.panel import Panel
            from rich.text import Text

            summary = Text()
            summary.append("Total Balance: ", style="bold white")
            summary.append(f"${total:,.2f}\n", style="bold cyan")
            summary.append("Assets: ", style="white")
            summary.append(f"${asset_total:,.2f}\n", style="green")
            summary.append("Liabilities: ", style="white")
            summary.append(f"${liability_total:,.2f}", style="red")

            panel = Panel(summary, title="[bold]Account Summary[/bold]", border_style="cyan")
            console.print(panel)
            logger.info(f"Balance check: ${total:.2f}")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            logger.error(f"Balance check failed: {str(e)}")
            raise click.Abort()

    asyncio.run(get_balance())


# Register command groups
cli.add_command(transactions)
cli.add_command(budgets)
cli.add_command(insights)
cli.add_command(chat)


if __name__ == '__main__':
    cli(obj={})
