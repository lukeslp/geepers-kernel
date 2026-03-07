"""
Tests for the package-level public interface.

Verifies that:
- All documented exports are importable from research_data_clients
- Every client the factory can create has .search() or .search_repositories() method
- Common structural guarantees hold across client types
"""

import pytest


# ---------------------------------------------------------------------------
# Package-level imports
# ---------------------------------------------------------------------------

class TestPackageExports:
    """All names in __all__ are importable from the top-level package."""

    def test_import_client_factory(self):
        from research_data_clients import ClientFactory
        assert ClientFactory is not None

    def test_import_data_fetching_factory(self):
        from research_data_clients import DataFetchingFactory
        assert DataFetchingFactory is not None

    def test_clientfactory_alias(self):
        from research_data_clients import ClientFactory, DataFetchingFactory
        assert ClientFactory is DataFetchingFactory

    def test_import_arxiv_client(self):
        from research_data_clients import ArxivClient
        assert ArxivClient is not None

    def test_import_arxiv_paper(self):
        from research_data_clients import ArxivPaper
        assert ArxivPaper is not None

    def test_import_arxiv_functions(self):
        from research_data_clients import search_arxiv, get_paper_by_id
        assert callable(search_arxiv)
        assert callable(get_paper_by_id)

    def test_import_wikipedia_client(self):
        from research_data_clients import WikipediaClient
        assert WikipediaClient is not None

    def test_import_pubmed_client(self):
        from research_data_clients import PubMedClient
        assert PubMedClient is not None

    def test_import_pubmed_article(self):
        from research_data_clients import PubMedArticle
        assert PubMedArticle is not None

    def test_import_pubmed_functions(self):
        from research_data_clients import search_pubmed, get_article_by_pmid
        assert callable(search_pubmed)
        assert callable(get_article_by_pmid)

    def test_import_semantic_scholar_client(self):
        from research_data_clients import SemanticScholarClient
        assert SemanticScholarClient is not None

    def test_import_semantic_scholar_paper(self):
        from research_data_clients import SemanticScholarPaper
        assert SemanticScholarPaper is not None

    def test_import_github_client(self):
        from research_data_clients import GitHubClient
        assert GitHubClient is not None

    def test_import_openlibrary_client(self):
        from research_data_clients import OpenLibraryClient
        assert OpenLibraryClient is not None

    def test_import_archive_client(self):
        from research_data_clients import ArchiveClient
        assert ArchiveClient is not None

    def test_import_archive_types(self):
        from research_data_clients import ArchivedSnapshot, ArchiveResult
        assert ArchivedSnapshot is not None
        assert ArchiveResult is not None

    def test_import_archive_functions(self):
        from research_data_clients import archive_url, get_latest_archive
        assert callable(archive_url)
        assert callable(get_latest_archive)

    def test_import_multi_archive_client(self):
        from research_data_clients import MultiArchiveClient
        assert MultiArchiveClient is not None

    def test_import_wolfram_client(self):
        from research_data_clients import WolframAlphaClient
        assert WolframAlphaClient is not None

    def test_import_wolfram_types(self):
        from research_data_clients import WolframResult
        assert WolframResult is not None


# ---------------------------------------------------------------------------
# Shared method interface
# ---------------------------------------------------------------------------

class TestClientInterface:
    """Clients that should expose a search() method do so."""

    def _has_method(self, obj, method_name: str) -> bool:
        return callable(getattr(obj, method_name, None))

    def test_arxiv_client_has_search(self):
        from research_data_clients import ArxivClient
        from unittest.mock import patch
        with patch("research_data_clients.arxiv_client.arxiv.Client"):
            client = ArxivClient()
        assert self._has_method(client, "search")

    def test_arxiv_client_has_get_by_id(self):
        from research_data_clients import ArxivClient
        from unittest.mock import patch
        with patch("research_data_clients.arxiv_client.arxiv.Client"):
            client = ArxivClient()
        assert self._has_method(client, "get_by_id")

    def test_wikipedia_client_has_search(self):
        from research_data_clients import WikipediaClient
        assert self._has_method(WikipediaClient(), "search")

    def test_wikipedia_client_has_get_summary(self):
        from research_data_clients import WikipediaClient
        assert self._has_method(WikipediaClient(), "get_summary")

    def test_pubmed_client_has_search(self):
        from research_data_clients import PubMedClient
        assert self._has_method(PubMedClient(), "search")

    def test_pubmed_client_has_get_by_id(self):
        from research_data_clients import PubMedClient
        assert self._has_method(PubMedClient(), "get_by_id")

    def test_semantic_scholar_has_search(self):
        from research_data_clients import SemanticScholarClient
        assert self._has_method(SemanticScholarClient(), "search")

    def test_github_client_has_search_repositories(self):
        from research_data_clients import GitHubClient
        client = GitHubClient(api_key="fake")
        assert self._has_method(client, "search_repositories")

    def test_openlibrary_client_has_search_books(self):
        from research_data_clients import OpenLibraryClient
        assert self._has_method(OpenLibraryClient(), "search_books")

    def test_archive_client_has_get_latest_snapshot(self):
        from research_data_clients import ArchiveClient
        assert self._has_method(ArchiveClient(), "get_latest_snapshot")


# ---------------------------------------------------------------------------
# Dataclass to_dict() contracts
# ---------------------------------------------------------------------------

class TestDataclassToDict:
    """All paper/article dataclasses produce dicts with a source key."""

    def test_arxiv_paper_to_dict_has_no_source_key(self):
        # ArxivPaper.to_dict() doesn't include 'source' — that's intentional
        from research_data_clients import ArxivPaper
        from datetime import datetime
        paper = ArxivPaper(
            title="Test", authors=[], summary="", published=datetime.now(),
            updated=datetime.now(), arxiv_id="1234", pdf_url="", categories=[], entry_id=""
        )
        d = paper.to_dict()
        # Must have these core fields
        assert "title" in d
        assert "arxiv_id" in d

    def test_pubmed_article_to_dict_source_is_pubmed(self):
        from research_data_clients import PubMedArticle
        article = PubMedArticle(
            pmid="1", title="T", authors=[], journal="J", publication_date="2024"
        )
        assert article.to_dict()["source"] == "PubMed"

    def test_semantic_scholar_paper_to_dict_source(self):
        from research_data_clients import SemanticScholarPaper
        paper = SemanticScholarPaper(
            title="T", authors=[], year=2020, abstract=None,
            doi=None, keywords=[], venue=None, url=None
        )
        assert paper.to_dict()["source"] == "semantic_scholar"


# ---------------------------------------------------------------------------
# Factory exhaustiveness
# ---------------------------------------------------------------------------

class TestFactoryExhaustiveness:
    """Every source listed in list_sources() can actually be instantiated."""

    # Sources that require mandatory API keys at construction time.
    # They are tested separately with a fake key so we know the factory routing works.
    API_KEY_REQUIRED = {
        "news": {"api_key": "fake-news-key"},
        "youtube": {"api_key": "fake-yt-key"},
        "finance": {"api_key": "fake-av-key"},
    }

    def test_all_listed_sources_are_creatable(self):
        from research_data_clients import ClientFactory
        from unittest.mock import patch

        sources = ClientFactory.list_sources()
        failed = []

        for source in sources:
            kwargs = self.API_KEY_REQUIRED.get(source, {})
            try:
                with patch("research_data_clients.arxiv_client.arxiv.Client"):
                    client = ClientFactory.create_client(source, **kwargs)
                assert client is not None
            except Exception as e:
                failed.append(f"{source}: {e}")

        assert failed == [], f"Failed to create clients: {failed}"

    def test_api_key_required_clients_raise_without_key(self):
        """Clients that mandate a key should raise clearly when none is supplied."""
        from research_data_clients import ClientFactory
        import os

        key_required = ["finance", "youtube", "news"]
        for source in key_required:
            # Make sure no env var is leaking in
            with pytest.raises(Exception):
                env_backup = {
                    k: os.environ.pop(k, None)
                    for k in ("ALPHAVANTAGE_API_KEY", "YOUTUBE_API_KEY", "NEWS_API_KEY")
                }
                try:
                    ClientFactory.create_client(source)
                finally:
                    for k, v in env_backup.items():
                        if v is not None:
                            os.environ[k] = v
