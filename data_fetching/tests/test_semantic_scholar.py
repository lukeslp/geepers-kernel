"""
Tests for SemanticScholarClient.

All HTTP calls are intercepted with the `responses` library.
"""

import pytest
import responses as resp_lib
from requests.exceptions import ConnectionError

from research_data_clients import SemanticScholarClient, SemanticScholarPaper
from research_data_clients.semantic_scholar import search_papers, get_paper_by_doi
from tests.conftest import (
    SEMANTIC_SCHOLAR_SEARCH_RESPONSE,
    SEMANTIC_SCHOLAR_PAPER_RESPONSE,
)


SS_BASE = "https://api.semanticscholar.org/graph/v1"
SEARCH_URL = f"{SS_BASE}/paper/search"
PAPER_URL = f"{SS_BASE}/paper"


# ---------------------------------------------------------------------------
# SemanticScholarPaper dataclass
# ---------------------------------------------------------------------------

class TestSemanticScholarPaper:
    def _make_paper(self, **overrides):
        defaults = dict(
            title="Attention Is All You Need",
            authors=["Vaswani A", "Shazeer N"],
            year=2017,
            abstract="We propose the Transformer.",
            doi="10.48550/arXiv.1706.03762",
            keywords=["Transformers", "Attention"],
            venue="NeurIPS",
            url="https://www.semanticscholar.org/paper/abc123",
            paper_id="abc123",
            citation_count=80000,
            reference_count=42,
            influential_citation_count=5000,
        )
        defaults.update(overrides)
        return SemanticScholarPaper(**defaults)

    def test_fields_set_correctly(self):
        paper = self._make_paper()
        assert paper.title == "Attention Is All You Need"
        assert paper.year == 2017
        assert paper.citation_count == 80000

    def test_optional_fields_can_be_none(self):
        paper = SemanticScholarPaper(
            title="Test",
            authors=[],
            year=None,
            abstract=None,
            doi=None,
            keywords=[],
            venue=None,
            url=None,
        )
        assert paper.year is None
        assert paper.doi is None

    def test_to_dict_has_required_keys(self):
        paper = self._make_paper()
        d = paper.to_dict()
        for key in ("title", "authors", "year", "abstract", "doi",
                    "keywords", "venue", "url", "paper_id",
                    "citation_count", "source"):
            assert key in d

    def test_to_dict_source_is_semantic_scholar(self):
        paper = self._make_paper()
        assert paper.to_dict()["source"] == "semantic_scholar"

    def test_from_api_response_extracts_authors(self):
        paper = SemanticScholarPaper.from_api_response(SEMANTIC_SCHOLAR_PAPER_RESPONSE)
        assert "Vaswani A" in paper.authors

    def test_from_api_response_extracts_topics_as_keywords(self):
        data = {**SEMANTIC_SCHOLAR_SEARCH_RESPONSE["data"][0]}
        paper = SemanticScholarPaper.from_api_response(data)
        assert "Transformers" in paper.keywords
        assert "Attention" in paper.keywords

    def test_from_api_response_handles_missing_fields(self):
        paper = SemanticScholarPaper.from_api_response({"title": "Minimal"})
        assert paper.title == "Minimal"
        assert paper.year is None
        assert paper.authors == []


# ---------------------------------------------------------------------------
# SemanticScholarClient instantiation
# ---------------------------------------------------------------------------

class TestSemanticScholarClientInit:
    def test_default_no_api_key(self):
        client = SemanticScholarClient()
        assert client.api_key is None

    def test_api_key_stored(self):
        client = SemanticScholarClient(api_key="test-key")
        assert client.api_key == "test-key"

    def test_headers_without_api_key(self):
        client = SemanticScholarClient()
        headers = client._get_headers()
        assert "Accept" in headers
        assert "x-api-key" not in headers

    def test_headers_with_api_key(self):
        client = SemanticScholarClient(api_key="sk-testkey")
        headers = client._get_headers()
        assert headers["x-api-key"] == "sk-testkey"

    def test_created_via_factory(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("semantic_scholar")
        assert isinstance(client, SemanticScholarClient)

    def test_created_via_factory_alias(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("semanticscholar")
        assert isinstance(client, SemanticScholarClient)


# ---------------------------------------------------------------------------
# SemanticScholarClient.search()
# ---------------------------------------------------------------------------

class TestSemanticScholarSearch:
    @resp_lib.activate
    def test_search_returns_list_of_papers(self, semantic_scholar_client):
        resp_lib.add(resp_lib.GET, SEARCH_URL, json=SEMANTIC_SCHOLAR_SEARCH_RESPONSE, status=200)
        papers = semantic_scholar_client.search("transformers")
        assert isinstance(papers, list)
        assert len(papers) == 1
        assert isinstance(papers[0], SemanticScholarPaper)

    @resp_lib.activate
    def test_search_paper_fields_populated(self, semantic_scholar_client):
        resp_lib.add(resp_lib.GET, SEARCH_URL, json=SEMANTIC_SCHOLAR_SEARCH_RESPONSE, status=200)
        papers = semantic_scholar_client.search("transformers")
        paper = papers[0]
        assert paper.title == "Attention Is All You Need"
        assert paper.year == 2017
        assert paper.citation_count == 80000

    @resp_lib.activate
    def test_search_empty_data_returns_empty_list(self, semantic_scholar_client):
        resp_lib.add(resp_lib.GET, SEARCH_URL, json={"data": []}, status=200)
        papers = semantic_scholar_client.search("zzz no results")
        assert papers == []

    @resp_lib.activate
    def test_search_filters_papers_without_title(self, semantic_scholar_client):
        payload = {
            "data": [
                {"title": "Valid Paper", "authors": [], "year": 2020},
                {"title": None, "authors": [], "year": 2020},  # no title
            ]
        }
        resp_lib.add(resp_lib.GET, SEARCH_URL, json=payload, status=200)
        papers = semantic_scholar_client.search("test")
        # Papers without title are filtered by the implementation
        titles = [p.title for p in papers]
        assert "Valid Paper" in titles

    @resp_lib.activate
    def test_search_uses_default_fields(self, semantic_scholar_client):
        resp_lib.add(resp_lib.GET, SEARCH_URL, json={"data": []}, status=200)
        semantic_scholar_client.search("test")
        req_url = resp_lib.calls[0].request.url
        assert "fields=" in req_url
        assert "title" in req_url

    @resp_lib.activate
    def test_search_respects_limit_param(self, semantic_scholar_client):
        resp_lib.add(resp_lib.GET, SEARCH_URL, json={"data": []}, status=200)
        semantic_scholar_client.search("test", limit=5)
        req_url = resp_lib.calls[0].request.url
        assert "limit=5" in req_url

    @resp_lib.activate
    def test_search_network_error_raises(self, semantic_scholar_client):
        resp_lib.add(resp_lib.GET, SEARCH_URL, body=ConnectionError("refused"))
        with pytest.raises(Exception):
            semantic_scholar_client.search("test")

    @resp_lib.activate
    def test_search_http_429_raises(self, semantic_scholar_client):
        resp_lib.add(resp_lib.GET, SEARCH_URL, status=429)
        with pytest.raises(Exception):
            semantic_scholar_client.search("test")


# ---------------------------------------------------------------------------
# SemanticScholarClient.get_by_doi()
# ---------------------------------------------------------------------------

class TestSemanticScholarGetByDoi:
    @resp_lib.activate
    def test_get_by_doi_returns_paper(self, semantic_scholar_client):
        doi = "10.48550/arXiv.1706.03762"
        resp_lib.add(
            resp_lib.GET, f"{PAPER_URL}/{doi}",
            json=SEMANTIC_SCHOLAR_PAPER_RESPONSE,
            status=200,
        )
        paper = semantic_scholar_client.get_by_doi(doi)
        assert isinstance(paper, SemanticScholarPaper)
        assert paper.title == "Attention Is All You Need"

    @resp_lib.activate
    def test_get_by_doi_returns_none_on_404(self, semantic_scholar_client):
        doi = "10.9999/nonexistent"
        resp_lib.add(resp_lib.GET, f"{PAPER_URL}/{doi}", status=404)
        paper = semantic_scholar_client.get_by_doi(doi)
        assert paper is None

    @resp_lib.activate
    def test_get_by_doi_raises_on_other_errors(self, semantic_scholar_client):
        doi = "10.9999/error"
        resp_lib.add(resp_lib.GET, f"{PAPER_URL}/{doi}", status=500)
        with pytest.raises(Exception):
            semantic_scholar_client.get_by_doi(doi)


# ---------------------------------------------------------------------------
# SemanticScholarClient.get_by_arxiv_id()
# ---------------------------------------------------------------------------

class TestSemanticScholarGetByArxivId:
    @resp_lib.activate
    def test_get_by_arxiv_id_delegates_to_get_by_doi(self, semantic_scholar_client):
        arxiv_id = "1706.03762"
        # The method calls get_by_doi("arXiv:1706.03762")
        resp_lib.add(
            resp_lib.GET, f"{PAPER_URL}/arXiv:{arxiv_id}",
            json=SEMANTIC_SCHOLAR_PAPER_RESPONSE,
            status=200,
        )
        paper = semantic_scholar_client.get_by_arxiv_id(arxiv_id)
        assert paper is not None
        assert paper.title == "Attention Is All You Need"

    @resp_lib.activate
    def test_get_by_arxiv_id_strips_arxiv_prefix(self, semantic_scholar_client):
        resp_lib.add(
            resp_lib.GET, f"{PAPER_URL}/arXiv:1706.03762",
            json=SEMANTIC_SCHOLAR_PAPER_RESPONSE,
            status=200,
        )
        paper = semantic_scholar_client.get_by_arxiv_id("arxiv:1706.03762")
        assert paper is not None

    @resp_lib.activate
    def test_get_by_arxiv_id_strips_mixed_case_prefix(self, semantic_scholar_client):
        resp_lib.add(
            resp_lib.GET, f"{PAPER_URL}/arXiv:1706.03762",
            json=SEMANTIC_SCHOLAR_PAPER_RESPONSE,
            status=200,
        )
        paper = semantic_scholar_client.get_by_arxiv_id("arXiv:1706.03762")
        assert paper is not None


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

class TestSemanticScholarConvenienceFunctions:
    @resp_lib.activate
    def test_search_papers_returns_list_of_dicts(self):
        resp_lib.add(resp_lib.GET, SEARCH_URL, json=SEMANTIC_SCHOLAR_SEARCH_RESPONSE, status=200)
        results = search_papers("transformers", limit=1)
        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert "title" in results[0]
        assert results[0]["source"] == "semantic_scholar"

    @resp_lib.activate
    def test_get_paper_by_doi_returns_dict(self):
        doi = "10.48550/arXiv.1706.03762"
        resp_lib.add(
            resp_lib.GET, f"{PAPER_URL}/{doi}",
            json=SEMANTIC_SCHOLAR_PAPER_RESPONSE,
            status=200,
        )
        result = get_paper_by_doi(doi)
        assert isinstance(result, dict)
        assert result["title"] == "Attention Is All You Need"

    @resp_lib.activate
    def test_get_paper_by_doi_returns_none_for_missing(self):
        doi = "10.9999/missing"
        resp_lib.add(resp_lib.GET, f"{PAPER_URL}/{doi}", status=404)
        result = get_paper_by_doi(doi)
        assert result is None
