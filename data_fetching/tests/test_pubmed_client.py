"""
Tests for PubMedClient.

All HTTP calls are intercepted with the `responses` library.
PubMed uses a two-step flow: esearch (ID list) -> esummary (article data).
"""

import pytest
import responses as resp_lib
from requests.exceptions import ConnectionError, HTTPError

from research_data_clients import PubMedClient, PubMedArticle
from research_data_clients.pubmed_client import (
    PUBMED_SEARCH_URL,
    PUBMED_SUMMARY_URL,
    search_pubmed,
    get_article_by_pmid,
)
from tests.conftest import (
    PUBMED_SEARCH_RESPONSE,
    PUBMED_SUMMARY_RESPONSE,
    PUBMED_SINGLE_SUMMARY_RESPONSE,
)


# ---------------------------------------------------------------------------
# PubMedArticle dataclass
# ---------------------------------------------------------------------------

class TestPubMedArticle:
    def _make_article(self, **overrides):
        defaults = dict(
            pmid="38000001",
            title="CRISPR-Cas9 genome editing",
            authors=["Smith J", "Jones A"],
            journal="Nature Biotechnology",
            publication_date="2024",
        )
        defaults.update(overrides)
        return PubMedArticle(**defaults)

    def test_url_property(self):
        article = self._make_article()
        assert article.url == "https://pubmed.ncbi.nlm.nih.gov/38000001/"

    def test_to_dict_has_required_keys(self):
        article = self._make_article()
        d = article.to_dict()
        for key in ("pmid", "title", "authors", "journal", "publication_date",
                    "abstract", "doi", "url", "source"):
            assert key in d

    def test_to_dict_source_is_pubmed(self):
        article = self._make_article()
        assert article.to_dict()["source"] == "PubMed"

    def test_optional_fields_default_to_none(self):
        article = self._make_article()
        assert article.abstract is None
        assert article.doi is None
        assert article.publication_types is None
        assert article.keywords is None

    def test_from_summary_extracts_authors(self):
        data = PUBMED_SUMMARY_RESPONSE["result"]["38000001"]
        article = PubMedArticle.from_summary("38000001", data)
        assert "Smith J" in article.authors
        assert "Jones A" in article.authors

    def test_from_summary_extracts_doi(self):
        data = PUBMED_SUMMARY_RESPONSE["result"]["38000001"]
        article = PubMedArticle.from_summary("38000001", data)
        assert article.doi is not None
        assert "10.1038" in article.doi

    def test_from_summary_no_doi_when_empty_elocationid(self):
        data = PUBMED_SUMMARY_RESPONSE["result"]["38000002"]
        article = PubMedArticle.from_summary("38000002", data)
        assert article.doi is None

    def test_from_summary_uses_fulljournalname(self):
        data = PUBMED_SUMMARY_RESPONSE["result"]["38000001"]
        article = PubMedArticle.from_summary("38000001", data)
        assert article.journal == "Nature Biotechnology"

    def test_from_summary_falls_back_to_source(self):
        data = {
            "title": "Test",
            "authors": [],
            "source": "J Med",
            "pubdate": "2020",
            "elocationid": "",
        }
        article = PubMedArticle.from_summary("99", data)
        assert article.journal == "J Med"


# ---------------------------------------------------------------------------
# PubMedClient instantiation
# ---------------------------------------------------------------------------

class TestPubMedClientInit:
    def test_no_api_key(self):
        client = PubMedClient()
        assert client.api_key is None
        assert client.email is None

    def test_with_api_key(self):
        client = PubMedClient(api_key="testkey")
        assert client.api_key == "testkey"

    def test_with_email(self):
        client = PubMedClient(email="me@example.com")
        assert client.email == "me@example.com"

    def test_session_has_user_agent(self):
        client = PubMedClient()
        ua = client.session.headers.get("User-Agent", "")
        assert ua != ""

    def test_created_via_factory(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("pubmed")
        assert isinstance(client, PubMedClient)


# ---------------------------------------------------------------------------
# _add_api_params()
# ---------------------------------------------------------------------------

class TestAddApiParams:
    def test_adds_api_key_when_set(self):
        client = PubMedClient(api_key="mykey")
        params = client._add_api_params({"db": "pubmed"})
        assert params["api_key"] == "mykey"

    def test_adds_email_when_set(self):
        client = PubMedClient(email="x@x.com")
        params = client._add_api_params({"db": "pubmed"})
        assert params["email"] == "x@x.com"

    def test_no_extra_params_when_not_set(self):
        client = PubMedClient()
        params = client._add_api_params({"db": "pubmed"})
        assert "api_key" not in params
        assert "email" not in params


# ---------------------------------------------------------------------------
# PubMedClient.search() — two-step flow
# ---------------------------------------------------------------------------

class TestPubMedSearch:
    @resp_lib.activate
    def test_search_returns_list_of_articles(self, pubmed_client):
        resp_lib.add(resp_lib.GET, PUBMED_SEARCH_URL, json=PUBMED_SEARCH_RESPONSE, status=200)
        resp_lib.add(resp_lib.GET, PUBMED_SUMMARY_URL, json=PUBMED_SUMMARY_RESPONSE, status=200)
        articles = pubmed_client.search("CRISPR")
        assert isinstance(articles, list)
        assert len(articles) == 2
        assert all(isinstance(a, PubMedArticle) for a in articles)

    @resp_lib.activate
    def test_search_article_fields_populated(self, pubmed_client):
        resp_lib.add(resp_lib.GET, PUBMED_SEARCH_URL, json=PUBMED_SEARCH_RESPONSE, status=200)
        resp_lib.add(resp_lib.GET, PUBMED_SUMMARY_URL, json=PUBMED_SUMMARY_RESPONSE, status=200)
        articles = pubmed_client.search("CRISPR")
        article = articles[0]
        assert article.pmid == "38000001"
        assert article.title == "CRISPR-Cas9 genome editing: mechanisms and applications"
        assert article.journal == "Nature Biotechnology"
        assert len(article.authors) == 2

    @resp_lib.activate
    def test_search_empty_id_list_returns_empty(self, pubmed_client):
        resp_lib.add(
            resp_lib.GET, PUBMED_SEARCH_URL,
            json={"esearchresult": {"idlist": []}},
            status=200,
        )
        articles = pubmed_client.search("zzznoresultsxyz")
        assert articles == []

    @resp_lib.activate
    def test_search_invalid_sort_raises_value_error(self, pubmed_client):
        with pytest.raises(ValueError, match="Invalid sort_by"):
            pubmed_client.search("test", sort_by="alphabetical")

    @resp_lib.activate
    def test_search_network_error_raises(self, pubmed_client):
        resp_lib.add(resp_lib.GET, PUBMED_SEARCH_URL, body=ConnectionError("refused"))
        with pytest.raises(Exception):
            pubmed_client.search("CRISPR")

    @resp_lib.activate
    def test_search_http_500_raises(self, pubmed_client):
        resp_lib.add(resp_lib.GET, PUBMED_SEARCH_URL, status=500)
        with pytest.raises(Exception):
            pubmed_client.search("CRISPR")

    @resp_lib.activate
    def test_search_sends_retmax_from_max_results(self, pubmed_client):
        resp_lib.add(
            resp_lib.GET, PUBMED_SEARCH_URL,
            json={"esearchresult": {"idlist": []}},
            status=200,
        )
        pubmed_client.search("test", max_results=3)
        req_url = resp_lib.calls[0].request.url
        assert "retmax=3" in req_url

    @resp_lib.activate
    def test_search_with_journal_filter_appends_journal_term(self, pubmed_client):
        resp_lib.add(
            resp_lib.GET, PUBMED_SEARCH_URL,
            json={"esearchresult": {"idlist": []}},
            status=200,
        )
        pubmed_client.search("cancer", journal="Nature")
        req_url = resp_lib.calls[0].request.url
        assert "Journal" in req_url

    @resp_lib.activate
    def test_search_with_api_key_includes_key_in_request(self, pubmed_client_with_key):
        resp_lib.add(
            resp_lib.GET, PUBMED_SEARCH_URL,
            json={"esearchresult": {"idlist": []}},
            status=200,
        )
        pubmed_client_with_key.search("test")
        req_url = resp_lib.calls[0].request.url
        assert "api_key=test-api-key" in req_url


# ---------------------------------------------------------------------------
# PubMedClient.get_by_id()
# ---------------------------------------------------------------------------

class TestPubMedGetById:
    @resp_lib.activate
    def test_get_by_id_returns_article(self, pubmed_client):
        resp_lib.add(resp_lib.GET, PUBMED_SUMMARY_URL, json=PUBMED_SINGLE_SUMMARY_RESPONSE, status=200)
        article = pubmed_client.get_by_id("38000001")
        assert isinstance(article, PubMedArticle)
        assert article.pmid == "38000001"

    @resp_lib.activate
    def test_get_by_id_strips_pmid_prefix(self, pubmed_client):
        resp_lib.add(resp_lib.GET, PUBMED_SUMMARY_URL, json=PUBMED_SINGLE_SUMMARY_RESPONSE, status=200)
        article = pubmed_client.get_by_id("PMID:38000001")
        assert article is not None

    @resp_lib.activate
    def test_get_by_id_strips_lowercase_prefix(self, pubmed_client):
        resp_lib.add(resp_lib.GET, PUBMED_SUMMARY_URL, json=PUBMED_SINGLE_SUMMARY_RESPONSE, status=200)
        article = pubmed_client.get_by_id("pmid:38000001")
        assert article is not None

    @resp_lib.activate
    def test_get_by_id_returns_none_when_not_found(self, pubmed_client):
        resp_lib.add(
            resp_lib.GET, PUBMED_SUMMARY_URL,
            json={"result": {"uids": []}},
            status=200,
        )
        article = pubmed_client.get_by_id("00000000")
        assert article is None

    @resp_lib.activate
    def test_get_by_id_network_error_raises(self, pubmed_client):
        resp_lib.add(resp_lib.GET, PUBMED_SUMMARY_URL, body=ConnectionError("timeout"))
        with pytest.raises(Exception):
            pubmed_client.get_by_id("38000001")


# ---------------------------------------------------------------------------
# PubMedClient.get_by_ids()
# ---------------------------------------------------------------------------

class TestPubMedGetByIds:
    @resp_lib.activate
    def test_get_by_ids_returns_multiple_articles(self, pubmed_client):
        resp_lib.add(resp_lib.GET, PUBMED_SUMMARY_URL, json=PUBMED_SUMMARY_RESPONSE, status=200)
        articles = pubmed_client.get_by_ids(["38000001", "38000002"])
        assert len(articles) == 2

    @resp_lib.activate
    def test_get_by_ids_cleans_prefixes(self, pubmed_client):
        resp_lib.add(resp_lib.GET, PUBMED_SUMMARY_URL, json=PUBMED_SUMMARY_RESPONSE, status=200)
        articles = pubmed_client.get_by_ids(["PMID:38000001", "38000002"])
        # Should not raise and should call the API
        assert len(resp_lib.calls) == 1


# ---------------------------------------------------------------------------
# Specialised search methods
# ---------------------------------------------------------------------------

class TestPubMedSpecialisedSearches:
    def test_search_by_author_calls_search_with_author_query(self, pubmed_client):
        with pytest.MonkeyPatch().context() as mp:
            calls = []

            def fake_search(query, max_results=10, sort_by="relevance", **kwargs):
                calls.append(query)
                return []

            mp.setattr(pubmed_client, "search", fake_search)
            pubmed_client.search_by_author("Smith J")
            assert len(calls) == 1
            assert "[Author]" in calls[0]
            assert "Smith J" in calls[0]

    def test_search_by_mesh_appends_mesh_tag(self, pubmed_client):
        with pytest.MonkeyPatch().context() as mp:
            calls = []

            def fake_search(query, max_results=10, sort_by="relevance", **kwargs):
                calls.append(query)
                return []

            mp.setattr(pubmed_client, "search", fake_search)
            pubmed_client.search_by_mesh("Diabetes Mellitus")
            assert "[MeSH Terms]" in calls[0]

    def test_search_clinical_trials_adds_publication_type(self, pubmed_client):
        with pytest.MonkeyPatch().context() as mp:
            calls = []

            def fake_search(query, max_results=10, sort_by="relevance", **kwargs):
                calls.append(query)
                return []

            mp.setattr(pubmed_client, "search", fake_search)
            pubmed_client.search_clinical_trials("diabetes")
            assert "Clinical Trial" in calls[0]

    def test_search_reviews_adds_review_publication_type(self, pubmed_client):
        with pytest.MonkeyPatch().context() as mp:
            calls = []

            def fake_search(query, max_results=10, sort_by="relevance", **kwargs):
                calls.append(query)
                return []

            mp.setattr(pubmed_client, "search", fake_search)
            pubmed_client.search_reviews("cancer")
            assert "Review" in calls[0]


# ---------------------------------------------------------------------------
# format_article()
# ---------------------------------------------------------------------------

class TestPubMedFormatArticle:
    def test_format_article_contains_title(self, pubmed_client):
        article = PubMedArticle(
            pmid="1",
            title="Test Article Title",
            authors=["Smith J"],
            journal="Nature",
            publication_date="2024",
        )
        formatted = pubmed_client.format_article(article)
        assert "Test Article Title" in formatted

    def test_format_article_contains_journal(self, pubmed_client):
        article = PubMedArticle(
            pmid="1",
            title="Test",
            authors=["Smith J"],
            journal="Nature",
            publication_date="2024",
        )
        formatted = pubmed_client.format_article(article)
        assert "Nature" in formatted

    def test_format_article_with_index_contains_header(self, pubmed_client):
        article = PubMedArticle(
            pmid="1",
            title="Test",
            authors=[],
            journal="Nature",
            publication_date="2024",
        )
        formatted = pubmed_client.format_article(article, index=1)
        assert "Article #1" in formatted


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

class TestPubMedConvenienceFunctions:
    @resp_lib.activate
    def test_search_pubmed_returns_list_of_dicts(self):
        resp_lib.add(resp_lib.GET, PUBMED_SEARCH_URL, json=PUBMED_SEARCH_RESPONSE, status=200)
        resp_lib.add(resp_lib.GET, PUBMED_SUMMARY_URL, json=PUBMED_SUMMARY_RESPONSE, status=200)
        results = search_pubmed("CRISPR", max_results=2)
        assert isinstance(results, list)
        assert len(results) == 2
        assert isinstance(results[0], dict)
        assert "pmid" in results[0]

    @resp_lib.activate
    def test_get_article_by_pmid_returns_dict(self):
        resp_lib.add(resp_lib.GET, PUBMED_SUMMARY_URL, json=PUBMED_SINGLE_SUMMARY_RESPONSE, status=200)
        result = get_article_by_pmid("38000001")
        assert isinstance(result, dict)
        assert result["pmid"] == "38000001"

    @resp_lib.activate
    def test_get_article_by_pmid_returns_none_for_missing(self):
        resp_lib.add(
            resp_lib.GET, PUBMED_SUMMARY_URL,
            json={"result": {"uids": []}},
            status=200,
        )
        result = get_article_by_pmid("00000000")
        assert result is None
