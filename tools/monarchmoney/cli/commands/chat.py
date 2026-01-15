"""Interactive chat mode with financial context."""

import asyncio
import sys
import os
import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

# Add shared library to path
sys.path.insert(0, os.path.expanduser('~/shared'))

from llm_providers import get_provider, Message
from monarchmoney.logger import logger

console = Console()


@click.command()
@click.option('--provider', '-p', default='anthropic', help='LLM provider')
@click.option('--model', '-m', help='Specific model to use')
def chat(provider, model):
    """Start an interactive chat session with financial context."""
    async def run_chat():
        from monarchmoney.monarchmoney import MonarchMoney

        try:
            # Load financial data once
            console.print("[dim]Loading your financial data...[/dim]")
            mm = MonarchMoney(use_secure_storage=True)
            await mm.login(use_saved_session=True)

            accounts = await mm.get_accounts()
            transactions = await mm.get_transactions(limit=500)

            try:
                budgets = await mm.get_budgets()
            except Exception as e:
                logger.warning(f"Failed to load budgets: {e}")
                budgets = {}

            try:
                cashflow = await mm.get_cashflow_summary()
            except Exception as e:
                logger.warning(f"Failed to load cashflow: {e}")
                cashflow = {}

            # Build context
            from cli.commands.insights import _build_financial_context
            financial_context = _build_financial_context(accounts, transactions, budgets, cashflow)

            # Initialize LLM
            llm = get_provider(provider, model=model)

            # Chat loop
            console.print(Panel(
                "[bold green]Financial Chat Assistant[/bold green]\n\n"
                "Ask me anything about your finances. Type 'exit' or 'quit' to end the session.",
                border_style="green"
            ))

            conversation_history = [
                Message(role="system", content=CHAT_SYSTEM_PROMPT),
                Message(role="system", content=f"Current Financial Data:\n{financial_context}")
            ]

            while True:
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

                if user_input.lower() in ['exit', 'quit', 'bye']:
                    console.print("[dim]Goodbye![/dim]")
                    break

                # Add to history
                conversation_history.append(Message(role="user", content=user_input))

                # Get response
                console.print("[dim]Thinking...[/dim]", end="\r")
                response = llm.complete(conversation_history, max_tokens=800)

                # Display response
                console.print(Panel(
                    Markdown(response.content),
                    title="[bold green]Assistant[/bold green]",
                    border_style="green"
                ))

                # Add to history
                conversation_history.append(Message(role="assistant", content=response.content))

                logger.debug(f"Chat exchange: User: '{user_input}', Assistant: '{response.content[:100]}...'")

        except KeyboardInterrupt:
            console.print("\n[dim]Chat session interrupted.[/dim]")
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
            logger.error(f"Chat session error: {str(e)}")
            raise click.Abort()

    asyncio.run(run_chat())


CHAT_SYSTEM_PROMPT = """You are a friendly financial assistant helping someone manage their finances.

You have access to their current financial data (accounts, transactions, budgets, cashflow).

Your role:
- Answer questions about their spending, income, and budgets
- Provide insights and recommendations
- Help them understand their financial situation
- Be conversational and supportive
- Use specific numbers from their data when relevant

Keep responses concise (2-4 paragraphs) unless asked for more detail.
Use markdown formatting to make responses clear and scannable.
"""
