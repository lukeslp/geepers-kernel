"""LLM-powered financial insights and analysis."""

import asyncio
import sys
import os
import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add shared library to path
sys.path.insert(0, os.path.expanduser('~/shared'))

from llm_providers import get_provider, Message
from monarchmoney.logger import logger

console = Console()


@click.group()
def insights():
    """Get LLM-powered financial insights."""
    pass


@insights.command('ask')
@click.argument('question')
@click.option('--provider', '-p', default='anthropic', help='LLM provider (anthropic, openai, xai)')
@click.option('--model', '-m', help='Specific model to use')
def ask_question(question, provider, model):
    """Ask a natural language question about your finances."""
    async def process_question():
        from monarchmoney.monarchmoney import MonarchMoney

        try:
            # Get financial data
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Fetching financial data...", total=None)
                mm = MonarchMoney(use_secure_storage=True)
                await mm.login(use_saved_session=True)

                # Gather comprehensive context
                progress.update(task, description="Loading accounts...")
                accounts = await mm.get_accounts()

                progress.update(task, description="Loading transactions...")
                transactions = await mm.get_transactions(limit=500)

                progress.update(task, description="Loading budgets...")
                try:
                    budgets = await mm.get_budgets()
                except Exception as e:
                    logger.warning(f"Failed to load budgets: {e}")
                    budgets = {}

                progress.update(task, description="Loading cashflow...")
                try:
                    cashflow = await mm.get_cashflow_summary()
                except Exception as e:
                    logger.warning(f"Failed to load cashflow: {e}")
                    cashflow = {}

            # Build context for LLM
            context = _build_financial_context(accounts, transactions, budgets, cashflow)

            # Query LLM
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task(f"Asking {provider}...", total=None)

                llm = get_provider(provider, model=model)
                messages = [
                    Message(role="system", content=FINANCIAL_ADVISOR_PROMPT),
                    Message(role="user", content=f"Financial Data:\n{context}\n\nQuestion: {question}")
                ]

                response = llm.complete(messages, max_tokens=1000)

            # Display response
            console.print(Panel(
                Markdown(response.content),
                title=f"[bold green]Financial Insights[/bold green]",
                border_style="green"
            ))

            logger.info(f"Insights query: '{question}' using {provider}")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            logger.error(f"Insights query failed: {str(e)}")
            raise click.Abort()

    asyncio.run(process_question())


@insights.command('analyze')
@click.option('--provider', '-p', default='anthropic', help='LLM provider')
def analyze_spending(provider):
    """Get a comprehensive spending analysis."""
    async def do_analysis():
        from monarchmoney.monarchmoney import MonarchMoney

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task("Analyzing your finances...", total=None)

                mm = MonarchMoney(use_secure_storage=True)
                await mm.login(use_saved_session=True)

                # Get comprehensive data
                transactions = await mm.get_transactions(limit=500)
                try:
                    cashflow = await mm.get_cashflow_summary()
                except Exception as e:
                    logger.warning(f"Failed to load cashflow: {e}")
                    cashflow = {}

                try:
                    budgets = await mm.get_budgets()
                except Exception as e:
                    logger.warning(f"Failed to load budgets: {e}")
                    budgets = {}

            # Build analysis prompt
            context = _build_financial_context({}, transactions, budgets, cashflow)

            llm = get_provider(provider)
            messages = [
                Message(role="system", content=FINANCIAL_ADVISOR_PROMPT),
                Message(role="user", content=f"""
Analyze this financial data and provide:
1. Top 3 spending categories
2. Budget adherence assessment
3. Savings opportunities
4. Recommended actions

Financial Data:
{context}
""")
            ]

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task("Generating insights...", total=None)
                response = llm.complete(messages, max_tokens=1500)

            console.print(Panel(
                Markdown(response.content),
                title="[bold cyan]Spending Analysis[/bold cyan]",
                border_style="cyan"
            ))

            logger.info(f"Spending analysis completed using {provider}")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            logger.error(f"Analysis failed: {str(e)}")
            raise click.Abort()

    asyncio.run(do_analysis())


def _build_financial_context(accounts, transactions, budgets, cashflow):
    """Build a concise financial context for LLM."""
    context_parts = []

    # Cashflow summary
    if cashflow:
        summary = cashflow.get('summary', {})
        context_parts.append(f"Monthly Summary:")
        context_parts.append(f"  Income: ${summary.get('sumIncome', 0):,.2f}")
        context_parts.append(f"  Expenses: ${abs(summary.get('sumExpense', 0)):,.2f}")
        context_parts.append(f"  Net: ${summary.get('sumIncome', 0) + summary.get('sumExpense', 0):,.2f}")
        context_parts.append("")

    # Budget data
    if budgets and 'monthlyBudgetData' in budgets:
        context_parts.append("Budgets:")
        for budget in budgets['monthlyBudgetData'][:10]:  # Top 10
            category = budget.get('category', {}).get('name', 'Unknown')
            budgeted = budget.get('budgetAmount', 0)
            spent = abs(budget.get('spentAmount', 0))
            context_parts.append(f"  {category}: Budgeted ${budgeted:.2f}, Spent ${spent:.2f}")
        context_parts.append("")

    # Recent transactions (summarized)
    if transactions:
        txn_list = transactions.get('allTransactions', {}).get('results', [])
        context_parts.append(f"Recent Transactions (last {len(txn_list)} transactions):")

        # Group by category
        by_category = {}
        for txn in txn_list[:100]:  # Last 100
            cat = txn.get('category', {}).get('name', 'Uncategorized')
            amount = abs(txn.get('amount', 0))
            by_category[cat] = by_category.get(cat, 0) + amount

        for cat, total in sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:10]:
            context_parts.append(f"  {cat}: ${total:,.2f}")

    return "\n".join(context_parts)


FINANCIAL_ADVISOR_PROMPT = """You are a helpful financial advisor analyzing personal finance data.

The user is new to managing inherited money and needs:
- Clear, actionable insights
- Identification of spending patterns
- Savings opportunities
- Budget optimization suggestions

Provide analysis that is:
- Empathetic and educational, not condescending
- Specific with dollar amounts when relevant
- Focused on top 3-5 most impactful insights
- Actionable with concrete next steps

Format responses in markdown with headers, bullet points, and emphasis where helpful.
"""
