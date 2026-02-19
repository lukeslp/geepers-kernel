import click
from geepers_kernel.config import ConfigManager
from geepers_kernel.providers import ProviderFactory
from geepers_kernel.clients import ClientFactory

@click.group()
def cli():
    """Geepers Kernel CLI for managing and testing library components."""
    pass

@cli.command()
@click.option('--provider', default='openai', help='LLM provider to test')
def test_provider(provider):
    """Test connection to a specific LLM provider."""
    config = ConfigManager()
    factory = ProviderFactory(config)
    try:
        provider_instance = factory.get_provider(provider)
        click.echo(f"Successfully connected to {provider} provider.")
    except Exception as e:
        click.echo(f"Failed to connect to {provider}: {str(e)}", err=True)

@cli.command()
@click.option('--client', default='wikipedia', help='Data API client to test')
def test_client(client):
    """Test connection to a specific data API client."""
    config = ConfigManager()
    factory = ClientFactory(config)
    try:
        client_instance = factory.get_client(client)
        click.echo(f"Successfully connected to {client} client.")
    except Exception as e:
        click.echo(f"Failed to connect to {client}: {str(e)}", err=True)

if __name__ == '__main__':
    cli()
