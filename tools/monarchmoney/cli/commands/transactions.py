"""Transaction management commands."""

import asyncio
import json
from datetime import date, timedelta
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from monarchmoney.logger import logger
from monarchmoney.validators import validate_date_string, validate_limit

console = Console()


@click.group()
def transactions():
    """Manage and view transactions."""
    pass


@transactions.command('list')
@click.option('--start', '-s', help='Start date (YYYY-MM-DD)')
@click.option('--end', '-e', help='End date (YYYY-MM-DD)')
@click.option('--limit', '-l', default=50, help='Number of transactions (max 500)')
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
def list_transactions(start, end, limit, output_json):
    """List recent transactions."""
    # Validate inputs
    try:
        if start:
            start_date = validate_date_string(start)
        else:
            start_date = (date.today() - timedelta(days=30))

        if end:
            end_date = validate_date_string(end)
        else:
            end_date = date.today()

        limit = validate_limit(limit, max_limit=500)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort()

    async def get_transactions():
        from monarchmoney.monarchmoney import MonarchMoney
        mm = MonarchMoney(use_secure_storage=True)

        try:
            await mm.login(use_saved_session=True)

            # Apply date filters if provided
            filter_params = {'limit': limit}
            if start:
                filter_params['start_date'] = start_date.isoformat()
            if end:
                filter_params['end_date'] = end_date.isoformat()

            transactions = await mm.get_transactions(**filter_params)

            if output_json:
                console.print_json(json.dumps(transactions, indent=2, default=str))
            else:
                table = Table(title=f"Transactions ({start_date} to {end_date})")
                table.add_column("Date", style="cyan")
                table.add_column("Description", style="white", no_wrap=False)
                table.add_column("Category", style="magenta")
                table.add_column("Amount", justify="right", style="green")

                for txn in transactions.get('allTransactions', {}).get('results', [])[:limit]:
                    amount = txn.get('amount', 0)
                    amount_str = f"${abs(amount):,.2f}"
                    amount_style = "red" if amount < 0 else "green"

                    table.add_row(
                        txn.get('date', 'N/A'),
                        txn.get('merchant', {}).get('name', txn.get('notes', 'N/A'))[:50],
                        txn.get('category', {}).get('name', 'Uncategorized'),
                        f"[{amount_style}]{amount_str}[/{amount_style}]"
                    )

                console.print(table)
                logger.info(f"Listed {limit} transactions")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            logger.error(f"Failed to list transactions: {str(e)}")
            raise click.Abort()

    asyncio.run(get_transactions())


@transactions.command('search')
@click.argument('query')
@click.option('--limit', '-l', default=20, help='Number of results')
def search_transactions(query, limit):
    """Search transactions by description or merchant."""
    try:
        limit = validate_limit(limit)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort()

    async def do_search():
        from monarchmoney.monarchmoney import MonarchMoney
        mm = MonarchMoney(use_secure_storage=True)

        try:
            await mm.login(use_saved_session=True)
            transactions = await mm.get_transactions(limit=500)

            # Filter transactions by query
            results = []
            for txn in transactions.get('allTransactions', {}).get('results', []):
                merchant = txn.get('merchant', {}).get('name', '')
                notes = txn.get('notes', '')
                if query.lower() in merchant.lower() or query.lower() in notes.lower():
                    results.append(txn)
                    if len(results) >= limit:
                        break

            if not results:
                console.print(f"[yellow]No transactions found matching '{query}'[/yellow]")
                return

            table = Table(title=f"Search Results for '{query}'")
            table.add_column("Date", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Amount", justify="right", style="green")

            for txn in results:
                amount = txn.get('amount', 0)
                amount_str = f"${abs(amount):,.2f}"
                amount_style = "red" if amount < 0 else "green"

                table.add_row(
                    txn.get('date', 'N/A'),
                    txn.get('merchant', {}).get('name', txn.get('notes', 'N/A')),
                    f"[{amount_style}]{amount_str}[/{amount_style}]"
                )

            console.print(table)
            console.print(f"\n[dim]Found {len(results)} matching transactions[/dim]")
            logger.info(f"Search '{query}' returned {len(results)} results")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            logger.error(f"Search failed: {str(e)}")
            raise click.Abort()

    asyncio.run(do_search())
