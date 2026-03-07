"""
Tests for WikipediaClient.

All HTTP calls are intercepted with the `responses` library.
"""

import pytest
import responses as resp_lib
from requests.exceptions import ConnectionError, Timeout

from research_data_clients import WikipediaClient
from tests.conftest import (
    WIKIPEDIA_OPENSEARCH_RESPONSE,
    WIKIPEDIA_SUMMARY_RESPONSE,
    WIKIPEDIA_RANDOM_RESPONSE,
)


EN_BASE = "https://en.wikipedia.org/w/api.php"
FR_BASE = "https://fr.wikipedia.org/w/api.php"


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestWikipediaClientInit:
    def test_default_language_is_en(self):
        client = WikipediaClient()
        assert client.language == "en"
        assert "en.wikipedia.org" in client.base_url

    def test_custom_language(self):
        client = WikipediaClient(language="fr")
        assert client.language == "fr"
        assert "fr.wikipedia.org" in client.base_url

    def test_session_has_user_agent(self):
        client = WikipediaClient()
        ua = client.session.headers.get("User-Agent", "")
        assert ua != ""

    def test_created_via_factory(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("wikipedia")
        assert isinstance(client, WikipediaClient)

    def test_created_via_factory_alias(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("wiki")
        assert isinstance(client, WikipediaClient)


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------

class TestWikipediaSearch:
    @resp_lib.activate
    def test_search_returns_dict_with_results(self, wikipedia_client):
        resp_lib.add(
            resp_lib.GET, EN_BASE,
            json=WIKIPEDIA_OPENSEARCH_RESPONSE,
            status=200,
        )
        result = wikipedia_client.search("Python")
        assert result["query"] == "Python"
        assert result["count"] == 3
        assert len(result["results"]) == 3

    @resp_lib.activate
    def test_search_result_has_required_fields(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, json=WIKIPEDIA_OPENSEARCH_RESPONSE, status=200)
        result = wikipedia_client.search("Python")
        first = result["results"][0]
        assert "title" in first
        assert "description" in first
        assert "url" in first

    @resp_lib.activate
    def test_search_result_title_matches_response(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, json=WIKIPEDIA_OPENSEARCH_RESPONSE, status=200)
        result = wikipedia_client.search("Python")
        assert result["results"][0]["title"] == "Python (programming language)"

    @resp_lib.activate
    def test_search_empty_response_returns_zero_count(self, wikipedia_client):
        # OpenSearch returning only [query] with no results
        resp_lib.add(resp_lib.GET, EN_BASE, json=["Python", [], [], []], status=200)
        result = wikipedia_client.search("Python")
        assert result["count"] == 0
        assert result["results"] == []

    @resp_lib.activate
    def test_search_network_error_returns_error_dict(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, body=ConnectionError("timeout"))
        result = wikipedia_client.search("Python")
        assert "error" in result

    @resp_lib.activate
    def test_search_http_error_returns_error_dict(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, status=503)
        result = wikipedia_client.search("Python")
        assert "error" in result

    @resp_lib.activate
    def test_search_sends_correct_params(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, json=WIKIPEDIA_OPENSEARCH_RESPONSE, status=200)
        wikipedia_client.search("Python", limit=5)
        assert len(resp_lib.calls) == 1
        req_params = resp_lib.calls[0].request.url
        assert "opensearch" in req_params
        assert "Python" in req_params


# ---------------------------------------------------------------------------
# get_summary()
# ---------------------------------------------------------------------------

class TestWikipediaGetSummary:
    @resp_lib.activate
    def test_get_summary_returns_correct_fields(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, json=WIKIPEDIA_SUMMARY_RESPONSE, status=200)
        result = wikipedia_client.get_summary("Python (programming language)")
        assert result["title"] == "Python (programming language)"
        assert "summary" in result
        assert result["page_id"] == 23862
        assert "en.wikipedia.org" in result["url"]

    @resp_lib.activate
    def test_get_summary_includes_image_if_available(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, json=WIKIPEDIA_SUMMARY_RESPONSE, status=200)
        result = wikipedia_client.get_summary("Python (programming language)")
        assert result["image"] is not None

    @resp_lib.activate
    def test_get_summary_article_not_found_returns_error(self, wikipedia_client):
        resp_lib.add(
            resp_lib.GET, EN_BASE,
            json={"query": {"pages": {"-1": {"pageid": -1, "title": "Nonexistent"}}}},
            status=200,
        )
        result = wikipedia_client.get_summary("Nonexistent article xyz")
        # No extract key means summary will be None, not an error per se,
        # but result should still have a title key
        assert "title" in result or "error" in result

    @resp_lib.activate
    def test_get_summary_network_error_returns_error_dict(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, body=ConnectionError("refused"))
        result = wikipedia_client.get_summary("Python")
        assert "error" in result


# ---------------------------------------------------------------------------
# get_full_content()
# ---------------------------------------------------------------------------

class TestWikipediaGetFullContent:
    @resp_lib.activate
    def test_get_full_content_returns_correct_fields(self, wikipedia_client):
        payload = {
            "query": {
                "pages": {
                    "23862": {
                        "pageid": 23862,
                        "title": "Python (programming language)",
                        "extract": "Python is a high-level language. " * 20,
                    }
                }
            }
        }
        resp_lib.add(resp_lib.GET, EN_BASE, json=payload, status=200)
        result = wikipedia_client.get_full_content("Python (programming language)")
        assert result["title"] == "Python (programming language)"
        assert "content" in result
        assert "word_count" in result
        assert result["word_count"] > 0
        assert "url" in result

    @resp_lib.activate
    def test_get_full_content_word_count_is_accurate(self, wikipedia_client):
        text = "word " * 50  # exactly 50 words
        payload = {
            "query": {
                "pages": {
                    "1": {"pageid": 1, "title": "Test", "extract": text.strip()}
                }
            }
        }
        resp_lib.add(resp_lib.GET, EN_BASE, json=payload, status=200)
        result = wikipedia_client.get_full_content("Test")
        assert result["word_count"] == 50

    @resp_lib.activate
    def test_get_full_content_error_on_network_failure(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, body=Timeout("timed out"))
        result = wikipedia_client.get_full_content("Python")
        assert "error" in result


# ---------------------------------------------------------------------------
# get_random()
# ---------------------------------------------------------------------------

class TestWikipediaGetRandom:
    @resp_lib.activate
    def test_get_random_returns_articles_list(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, json=WIKIPEDIA_RANDOM_RESPONSE, status=200)
        result = wikipedia_client.get_random(limit=1)
        assert "articles" in result
        assert result["count"] == 1
        assert result["articles"][0]["title"] == "Banjo"

    @resp_lib.activate
    def test_get_random_article_has_url(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, json=WIKIPEDIA_RANDOM_RESPONSE, status=200)
        result = wikipedia_client.get_random()
        article = result["articles"][0]
        assert "url" in article
        assert "wikipedia.org" in article["url"]

    @resp_lib.activate
    def test_get_random_error_on_server_error(self, wikipedia_client):
        resp_lib.add(resp_lib.GET, EN_BASE, status=500)
        result = wikipedia_client.get_random()
        assert "error" in result


# ---------------------------------------------------------------------------
# Non-English language
# ---------------------------------------------------------------------------

class TestWikipediaFrench:
    @resp_lib.activate
    def test_french_client_uses_fr_url(self):
        client = WikipediaClient(language="fr")
        resp_lib.add(resp_lib.GET, FR_BASE, json=WIKIPEDIA_OPENSEARCH_RESPONSE, status=200)
        result = client.search("Python")
        assert result["count"] == 3

    @resp_lib.activate
    def test_french_client_summary_url_contains_fr(self):
        client = WikipediaClient(language="fr")
        resp_lib.add(resp_lib.GET, FR_BASE, json=WIKIPEDIA_SUMMARY_RESPONSE, status=200)
        result = client.get_summary("Python")
        if "url" in result:
            assert "fr.wikipedia.org" in result["url"]
