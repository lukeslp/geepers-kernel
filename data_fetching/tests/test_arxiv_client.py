"""
Tests for ArxivClient.

The arxiv library's Client is mocked at the point of use so no real
network calls are made. We verify the conversion from arxiv.Result
objects to ArxivPaper dataclasses and the public interface.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from research_data_clients import ArxivClient, ArxivPaper


# ---------------------------------------------------------------------------
# ArxivPaper dataclass tests
# ---------------------------------------------------------------------------

class TestArxivPaper:
    """ArxivPaper construction, conversion, and helper methods."""

    def _make_paper(self, **overrides):
        defaults = dict(
            title="Attention Is All You Need",
            authors=["Vaswani A", "Shazeer N"],
            summary="We propose the Transformer.",
            published=datetime(2017, 6, 12),
            updated=datetime(2017, 12, 6),
            arxiv_id="1706.03762",
            pdf_url="https://arxiv.org/pdf/1706.03762",
            categories=["cs.CL", "cs.LG"],
            entry_id="https://arxiv.org/abs/1706.03762",
        )
        defaults.update(overrides)
        return ArxivPaper(**defaults)

    def test_basic_fields_set_correctly(self):
        paper = self._make_paper()
        assert paper.title == "Attention Is All You Need"
        assert paper.authors == ["Vaswani A", "Shazeer N"]
        assert paper.arxiv_id == "1706.03762"

    def test_optional_fields_default_to_none(self):
        paper = self._make_paper()
        assert paper.doi is None
        assert paper.comment is None
        assert paper.journal_ref is None
        assert paper.primary_category is None

    def test_to_dict_contains_required_keys(self):
        paper = self._make_paper()
        d = paper.to_dict()
        for key in ("title", "authors", "summary", "published", "updated",
                    "arxiv_id", "pdf_url", "categories", "entry_id"):
            assert key in d

    def test_to_dict_published_is_isoformat_string(self):
        paper = self._make_paper()
        d = paper.to_dict()
        # Should be a string, not a datetime object
        assert isinstance(d["published"], str)
        assert "2017" in d["published"]

    def test_from_arxiv_result(self, mock_arxiv_result):
        paper = ArxivPaper.from_arxiv_result(mock_arxiv_result)
        assert paper.title == "Attention Is All You Need"
        assert "Vaswani A" in paper.authors
        assert paper.arxiv_id == "1706.03762"
        assert paper.categories == ["cs.CL", "cs.LG"]
        assert paper.comment == "NeurIPS 2017"

    def test_from_arxiv_result_strips_prefix_from_id(self, mock_arxiv_result):
        mock_arxiv_result.entry_id = "https://arxiv.org/abs/2301.07041v2"
        paper = ArxivPaper.from_arxiv_result(mock_arxiv_result)
        assert paper.arxiv_id == "2301.07041v2"


# ---------------------------------------------------------------------------
# ArxivClient instantiation
# ---------------------------------------------------------------------------

class TestArxivClientInit:
    """ArxivClient can be created and has expected attributes."""

    def test_client_instantiates(self):
        with patch("research_data_clients.arxiv_client.arxiv.Client"):
            client = ArxivClient()
            assert hasattr(client, "client")

    def test_created_via_factory(self):
        from research_data_clients import ClientFactory
        with patch("research_data_clients.arxiv_client.arxiv.Client"):
            client = ClientFactory.create_client("arxiv")
            assert isinstance(client, ArxivClient)


# ---------------------------------------------------------------------------
# ArxivClient.search()
# ---------------------------------------------------------------------------

class TestArxivClientSearch:
    """search() calls the underlying arxiv client and returns ArxivPaper objects."""

    @pytest.fixture
    def client(self):
        with patch("research_data_clients.arxiv_client.arxiv.Client") as MockClient:
            instance = ArxivClient()
            instance._mock_client = MockClient.return_value
            yield instance

    def _setup_mock_results(self, client, results):
        client._mock_client.results.return_value = iter(results)

    def test_search_returns_list_of_arxiv_papers(self, client, mock_arxiv_result):
        self._setup_mock_results(client, [mock_arxiv_result])
        papers = client.search("transformers")
        assert isinstance(papers, list)
        assert len(papers) == 1
        assert isinstance(papers[0], ArxivPaper)

    def test_search_paper_fields_populated(self, client, mock_arxiv_result):
        self._setup_mock_results(client, [mock_arxiv_result])
        papers = client.search("transformers")
        paper = papers[0]
        assert paper.title == "Attention Is All You Need"
        assert len(paper.authors) == 2

    def test_search_empty_results(self, client):
        self._setup_mock_results(client, [])
        papers = client.search("xyzzy nonexistent paper")
        assert papers == []

    def test_search_multiple_results(self, client, mock_arxiv_result):
        result2 = MagicMock()
        result2.title = "BERT: Pre-training Deep Bidirectional Transformers"
        result2.authors = [MagicMock(name="Devlin J")]
        result2.summary = "We introduce BERT."
        result2.published = datetime(2018, 10, 11)
        result2.updated = datetime(2019, 5, 24)
        result2.entry_id = "https://arxiv.org/abs/1810.04805"
        result2.pdf_url = "https://arxiv.org/pdf/1810.04805"
        result2.categories = ["cs.CL"]
        result2.doi = None
        result2.comment = None
        result2.journal_ref = None
        result2.primary_category = "cs.CL"

        self._setup_mock_results(client, [mock_arxiv_result, result2])
        papers = client.search("transformers", max_results=2)
        assert len(papers) == 2

    def test_search_invalid_sort_by_raises_value_error(self, client):
        with pytest.raises(ValueError, match="Invalid sort_by"):
            client.search("test", sort_by="popularity")

    def test_search_relevance_sort(self, client, mock_arxiv_result):
        import arxiv as arxiv_lib
        self._setup_mock_results(client, [mock_arxiv_result])
        client.search("test", sort_by="relevance")
        call_args = client.client.results.call_args
        search_obj = call_args[0][0]
        assert search_obj.sort_by == arxiv_lib.SortCriterion.Relevance

    def test_search_date_sort(self, client, mock_arxiv_result):
        import arxiv as arxiv_lib
        self._setup_mock_results(client, [mock_arxiv_result])
        client.search("test", sort_by="date")
        call_args = client.client.results.call_args
        search_obj = call_args[0][0]
        assert search_obj.sort_by == arxiv_lib.SortCriterion.LastUpdatedDate

    def test_search_raises_on_arxiv_exception(self, client):
        client.client.results.side_effect = Exception("API unavailable")
        with pytest.raises(Exception, match="API unavailable"):
            client.search("test")


# ---------------------------------------------------------------------------
# ArxivClient.get_by_id()
# ---------------------------------------------------------------------------

class TestArxivClientGetById:
    """get_by_id() fetches a single paper and handles missing papers."""

    @pytest.fixture
    def client(self):
        with patch("research_data_clients.arxiv_client.arxiv.Client") as MockClient:
            instance = ArxivClient()
            instance._mock_client = MockClient.return_value
            yield instance

    def test_get_by_id_returns_arxiv_paper(self, client, mock_arxiv_result):
        client.client.results.return_value = iter([mock_arxiv_result])
        paper = client.get_by_id("1706.03762")
        assert isinstance(paper, ArxivPaper)
        assert paper.title == "Attention Is All You Need"

    def test_get_by_id_strips_arxiv_prefix(self, client, mock_arxiv_result):
        client.client.results.return_value = iter([mock_arxiv_result])
        paper = client.get_by_id("arxiv:1706.03762")
        # Should find the paper and construct search with clean ID
        assert paper is not None

    def test_get_by_id_returns_none_when_not_found(self, client):
        client.client.results.return_value = iter([])
        paper = client.get_by_id("0000.00000")
        assert paper is None

    def test_get_by_id_passes_id_to_search(self, client, mock_arxiv_result):
        client.client.results.return_value = iter([mock_arxiv_result])
        client.get_by_id("1706.03762")
        call_args = client.client.results.call_args
        search_obj = call_args[0][0]
        assert "1706.03762" in search_obj.id_list


# ---------------------------------------------------------------------------
# ArxivClient specialised search methods
# ---------------------------------------------------------------------------

class TestArxivClientSpecialisedSearches:
    """search_by_author() and search_by_category() build correct queries."""

    @pytest.fixture
    def client(self):
        with patch("research_data_clients.arxiv_client.arxiv.Client") as MockClient:
            instance = ArxivClient()
            MockClient.return_value.results.return_value = iter([])
            yield instance

    def test_search_by_author_constructs_au_query(self, client):
        with patch.object(client, "search", return_value=[]) as mock_search:
            client.search_by_author("Yann LeCun")
            mock_search.assert_called_once_with('au:"Yann LeCun"', 10, "date")

    def test_search_by_category_constructs_cat_query(self, client):
        with patch.object(client, "search", return_value=[]) as mock_search:
            client.search_by_category("cs.AI")
            mock_search.assert_called_once_with("cat:cs.AI", 10, "date")


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

class TestArxivConvenienceFunctions:
    """Module-level search_arxiv() and get_paper_by_id() return dicts."""

    def test_search_arxiv_returns_list_of_dicts(self, mock_arxiv_result):
        from research_data_clients import search_arxiv
        with patch("research_data_clients.arxiv_client.arxiv.Client") as MockClient:
            MockClient.return_value.results.return_value = iter([mock_arxiv_result])
            results = search_arxiv("transformers", max_results=1)
        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert "title" in results[0]

    def test_get_paper_by_id_returns_dict(self, mock_arxiv_result):
        from research_data_clients import get_paper_by_id
        with patch("research_data_clients.arxiv_client.arxiv.Client") as MockClient:
            MockClient.return_value.results.return_value = iter([mock_arxiv_result])
            result = get_paper_by_id("1706.03762")
        assert isinstance(result, dict)
        assert result["title"] == "Attention Is All You Need"

    def test_get_paper_by_id_returns_none_for_missing(self):
        from research_data_clients import get_paper_by_id
        with patch("research_data_clients.arxiv_client.arxiv.Client") as MockClient:
            MockClient.return_value.results.return_value = iter([])
            result = get_paper_by_id("0000.00000")
        assert result is None
