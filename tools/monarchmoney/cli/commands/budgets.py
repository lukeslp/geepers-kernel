"""Budget management commands."""

import asyncio
import json
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from monarchmoney.logger import logger

console = Console()


@click.group()
def budgets():
    """Manage budgets and spending."""
    pass


@budgets.command('show')
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
def show_budgets(output_json):
    """Show current budget status."""
    async def get_budgets():
        from monarchmoney.monarchmoney import MonarchMoney
        mm = MonarchMoney(use_secure_storage=True)

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task("Fetching budgets...", total=None)
                await mm.login(use_saved_session=True)
                budgets_data = await mm.get_budgets()

            if output_json:
                console.print_json(json.dumps(budgets_data, indent=2, default=str))
            else:
                table = Table(title="Monthly Budgets")
                table.add_column("Category", style="cyan")
                table.add_column("Budgeted", justify="right", style="blue")
                table.add_column("Spent", justify="right", style="yellow")
                table.add_column("Remaining", justify="right", style="green")
                table.add_column("Status", style="magenta")

                for budget in budgets_data.get('monthlyBudgetData', []):
                    category_name = budget.get('category', {}).get('name', 'Unknown')
                    budgeted = budget.get('budgetAmount', 0)
                    spent = abs(budget.get('spentAmount', 0))
                    remaining = budgeted - spent
                    pct = (spent / budgeted * 100) if budgeted > 0 else 0

                    # Status indicator
                    if pct >= 100:
                        status = "[bold red]Over Budget![/bold red]"
                    elif pct >= 80:
                        status = "[yellow]⚠ Warning[/yellow]"
                    else:
                        status = "[green]✓ On Track[/green]"

                    table.add_row(
                        category_name,
                        f"${budgeted:,.2f}",
                        f"${spent:,.2f}",
                        f"${remaining:,.2f}",
                        status
                    )

                console.print(table)
                logger.info(f"Displayed {len(budgets_data.get('monthlyBudgetData', []))} budget categories")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            logger.error(f"Failed to fetch budgets: {str(e)}")
            raise click.Abort()

    asyncio.run(get_budgets())


@budgets.command('summary')
def budget_summary():
    """Show overall budget summary."""
    async def get_summary():
        from monarchmoney.monarchmoney import MonarchMoney
        mm = MonarchMoney(use_secure_storage=True)

        try:
            await mm.login(use_saved_session=True)
            cashflow = await mm.get_cashflow_summary()

            summary = cashflow.get('summary', {})
            total_income = summary.get('sumIncome', 0)
            total_expenses = abs(summary.get('sumExpense', 0))
            savings = total_income - total_expenses
            savings_rate = (savings / total_income * 100) if total_income > 0 else 0

            console.print("\n[bold]Monthly Budget Summary[/bold]\n")
            console.print(f"  Income:     [green]${total_income:,.2f}[/green]")
            console.print(f"  Expenses:   [red]${total_expenses:,.2f}[/red]")
            console.print(f"  [bold]Net:        [cyan]${savings:,.2f}[/cyan][/bold]")
            console.print(f"  Savings Rate: [magenta]{savings_rate:.1f}%[/magenta]\n")

            logger.info(f"Budget summary: Income ${total_income:.2f}, Expenses ${total_expenses:.2f}")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            logger.error(f"Failed to get budget summary: {str(e)}")
            raise click.Abort()

    asyncio.run(get_summary())
