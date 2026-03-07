"""
Tests for DataFetchingFactory / ClientFactory.

Verifies the factory creates the right client type for each source name,
handles aliases, and raises on unknown sources.
"""

import pytest
from research_data_clients import ClientFactory, DataFetchingFactory
from research_data_clients.factory import DataFetchingFactory as DirectFactory


class TestFactoryAlias:
    """ClientFactory is an alias for DataFetchingFactory."""

    def test_clientfactory_is_datafetchingfactory(self):
        assert ClientFactory is DataFetchingFactory

    def test_direct_import_same_class(self):
        assert ClientFactory is DirectFactory


class TestListSources:
    """DataFetchingFactory.list_sources() returns the expected catalogue."""

    def test_returns_list(self):
        sources = DataFetchingFactory.list_sources()
        assert isinstance(sources, list)

    def test_contains_core_sources(self):
        sources = DataFetchingFactory.list_sources()
        for expected in ("arxiv", "pubmed", "wikipedia", "github", "semantic_scholar"):
            assert expected in sources, f"Expected '{expected}' in list_sources()"

    def test_fourteen_sources(self):
        # Factory docstring lists 14 sources
        assert len(DataFetchingFactory.list_sources()) == 14


class TestCreateClientTypes:
    """create_client() returns the correct class for each source name."""

    def test_arxiv(self):
        from research_data_clients import ArxivClient
        client = ClientFactory.create_client("arxiv")
        assert isinstance(client, ArxivClient)

    def test_wikipedia(self):
        from research_data_clients import WikipediaClient
        client = ClientFactory.create_client("wikipedia")
        assert isinstance(client, WikipediaClient)

    def test_wikipedia_alias_wiki(self):
        from research_data_clients import WikipediaClient
        client = ClientFactory.create_client("wiki")
        assert isinstance(client, WikipediaClient)

    def test_pubmed(self):
        from research_data_clients import PubMedClient
        client = ClientFactory.create_client("pubmed")
        assert isinstance(client, PubMedClient)

    def test_semantic_scholar(self):
        from research_data_clients import SemanticScholarClient
        client = ClientFactory.create_client("semantic_scholar")
        assert isinstance(client, SemanticScholarClient)

    def test_semantic_scholar_alias_semanticscholar(self):
        from research_data_clients import SemanticScholarClient
        client = ClientFactory.create_client("semanticscholar")
        assert isinstance(client, SemanticScholarClient)

    def test_github(self):
        from research_data_clients import GitHubClient
        client = ClientFactory.create_client("github")
        assert isinstance(client, GitHubClient)

    def test_openlibrary(self):
        from research_data_clients import OpenLibraryClient
        client = ClientFactory.create_client("openlibrary")
        assert isinstance(client, OpenLibraryClient)

    def test_openlibrary_alias_books(self):
        from research_data_clients import OpenLibraryClient
        client = ClientFactory.create_client("books")
        assert isinstance(client, OpenLibraryClient)

    def test_archive(self):
        from research_data_clients import ArchiveClient
        client = ClientFactory.create_client("archive")
        assert isinstance(client, ArchiveClient)

    def test_archive_alias_wayback(self):
        from research_data_clients import ArchiveClient
        client = ClientFactory.create_client("wayback")
        assert isinstance(client, ArchiveClient)

    def test_nasa(self):
        from research_data_clients.nasa_client import NASAClient
        client = ClientFactory.create_client("nasa")
        assert isinstance(client, NASAClient)

    def test_weather(self):
        from research_data_clients.weather_client import WeatherClient
        client = ClientFactory.create_client("weather")
        assert isinstance(client, WeatherClient)

    def test_weather_alias_noaa(self):
        from research_data_clients.weather_client import WeatherClient
        client = ClientFactory.create_client("noaa")
        assert isinstance(client, WeatherClient)

    def test_finance(self):
        from research_data_clients.finance_client import FinanceClient
        client = ClientFactory.create_client("finance", api_key="test-key")
        assert isinstance(client, FinanceClient)

    def test_finance_alias_alphavantage(self):
        from research_data_clients.finance_client import FinanceClient
        client = ClientFactory.create_client("alphavantage", api_key="test-key")
        assert isinstance(client, FinanceClient)

    def test_wolfram(self):
        from research_data_clients.wolfram_client import WolframAlphaClient
        client = ClientFactory.create_client("wolfram")
        assert isinstance(client, WolframAlphaClient)

    def test_wolfram_alias_wolframalpha(self):
        from research_data_clients.wolfram_client import WolframAlphaClient
        client = ClientFactory.create_client("wolframalpha")
        assert isinstance(client, WolframAlphaClient)


class TestCreateClientCaseInsensitive:
    """Source names should be normalized to lowercase."""

    def test_uppercase_arxiv(self):
        from research_data_clients import ArxivClient
        client = ClientFactory.create_client("ARXIV")
        assert isinstance(client, ArxivClient)

    def test_mixed_case_pubmed(self):
        from research_data_clients import PubMedClient
        client = ClientFactory.create_client("PubMed")
        assert isinstance(client, PubMedClient)

    def test_uppercase_wikipedia(self):
        from research_data_clients import WikipediaClient
        client = ClientFactory.create_client("Wikipedia")
        assert isinstance(client, WikipediaClient)


class TestCreateClientKwargs:
    """Keyword arguments should be forwarded to client constructors."""

    def test_pubmed_api_key_forwarded(self):
        from research_data_clients import PubMedClient
        client = ClientFactory.create_client("pubmed", api_key="my-key")
        assert isinstance(client, PubMedClient)
        assert client.api_key == "my-key"

    def test_pubmed_email_forwarded(self):
        from research_data_clients import PubMedClient
        client = ClientFactory.create_client("pubmed", email="me@example.com")
        assert client.email == "me@example.com"

    def test_github_api_key_forwarded(self):
        from research_data_clients import GitHubClient
        client = ClientFactory.create_client("github", api_key="gh-token")
        assert isinstance(client, GitHubClient)
        assert client.api_key == "gh-token"

    def test_wikipedia_language_forwarded(self):
        from research_data_clients import WikipediaClient
        client = ClientFactory.create_client("wikipedia", language="fr")
        assert isinstance(client, WikipediaClient)
        assert client.language == "fr"


class TestCreateClientUnknownSource:
    """Unknown source names must raise ValueError."""

    def test_unknown_source_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown data source"):
            ClientFactory.create_client("not_a_real_source")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            ClientFactory.create_client("")

    def test_error_message_lists_available_sources(self):
        with pytest.raises(ValueError) as exc_info:
            ClientFactory.create_client("garbage")
        assert "arxiv" in str(exc_info.value)
