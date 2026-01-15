"""
Perplexity CLI Commands.

Author: Luke Steuber
"""

from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from ...utils import print_response, print_error, print_json, create_spinner
from .client import PerplexityProvider

app = typer.Typer(name="perplexity", help="Perplexity API commands (web-grounded)", no_args_is_help=True)
console = Console()


@app.command("chat")
def chat(
    prompt: str = typer.Argument(..., help="The prompt to send"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model (sonar-pro, sonar, sonar-reasoning)"),
    system: Optional[str] = typer.Option(None, "-s", "--system"),
    temperature: float = typer.Option(0.7, "-t", "--temperature"),
    max_tokens: int = typer.Option(4096, "--max-tokens"),
    no_stream: bool = typer.Option(False, "--no-stream"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Chat with Perplexity Sonar (web-grounded responses).

    Example: llm perplexity chat "What are the latest AI developments?"
    """
    try:
        provider = PerplexityProvider(model=model)
        from ...providers.base import Message
        messages = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))

        if no_stream or json_output:
            with create_spinner("Searching and thinking..."):
                response = provider.chat(messages=messages, temperature=temperature, max_tokens=max_tokens)
            if json_output:
                result = {
                    "content": response.content,
                    "model": response.model,
                    "usage": response.usage,
                }
                if response.metadata and response.metadata.get("citations"):
                    result["citations"] = response.metadata["citations"]
                print_json(result)
            else:
                print_response(response.content)
                # Show citations if available
                if response.metadata and response.metadata.get("citations"):
                    console.print("\n[bold]Sources:[/bold]")
                    for i, cite in enumerate(response.metadata["citations"], 1):
                        console.print(f"  [{i}] {cite}")
        else:
            full_response = ""
            with Live(Markdown(""), console=console, refresh_per_second=10) as live:
                for chunk in provider.chat_stream(messages=messages, temperature=temperature, max_tokens=max_tokens):
                    full_response += chunk
                    live.update(Markdown(full_response))
            console.print()
    except Exception as e:
        print_error(f"Chat failed: {e}")
        raise typer.Exit(1)


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search query"),
    model: Optional[str] = typer.Option("sonar", "-m", "--model"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Search the web with Perplexity.

    Example: llm perplexity search "latest news on climate change"
    """
    try:
        provider = PerplexityProvider(model=model)
        from ...providers.base import Message
        messages = [Message(role="user", content=query)]

        with create_spinner("Searching..."):
            response = provider.chat(messages=messages, temperature=0.3)

        if json_output:
            result = {
                "content": response.content,
                "model": response.model,
            }
            if response.metadata and response.metadata.get("citations"):
                result["citations"] = response.metadata["citations"]
            print_json(result)
        else:
            print_response(response.content, title="Search Results")
            if response.metadata and response.metadata.get("citations"):
                console.print("\n[bold]Sources:[/bold]")
                for i, cite in enumerate(response.metadata["citations"], 1):
                    console.print(f"  [{i}] {cite}")
    except Exception as e:
        print_error(f"Search failed: {e}")
        raise typer.Exit(1)


@app.command("models")
def models(json_output: bool = typer.Option(False, "--json")):
    """List available Perplexity models."""
    try:
        provider = PerplexityProvider()
        model_list = provider.list_models()
        if json_output:
            print_json(model_list)
        else:
            from rich.table import Table
            table = Table(title="Perplexity Models")
            table.add_column("Model", style="cyan")
            table.add_column("Description")
            table.add_column("Context", style="dim")
            for m in model_list:
                ctx = f"{m.get('context', 0) // 1000}K" if m.get('context') else ""
                table.add_row(m["name"], m.get("description", ""), ctx)
            console.print(table)
    except Exception as e:
        print_error(f"Failed to list models: {e}")
        raise typer.Exit(1)
