"""
Tests for OpenLibraryClient.

All HTTP calls are intercepted with the `responses` library.
"""

import pytest
import responses as resp_lib
from requests.exceptions import ConnectionError

from research_data_clients import OpenLibraryClient
from tests.conftest import OPENLIBRARY_SEARCH_RESPONSE, OPENLIBRARY_ISBN_RESPONSE


OL_BASE = "https://openlibrary.org"


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestOpenLibraryClientInit:
    def test_instantiates_successfully(self):
        client = OpenLibraryClient()
        assert client is not None

    def test_base_url_is_correct(self):
        client = OpenLibraryClient()
        assert client.BASE_URL == "https://openlibrary.org"

    def test_session_has_user_agent(self):
        client = OpenLibraryClient()
        assert client.session.headers.get("User-Agent", "") != ""

    def test_created_via_factory(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("openlibrary")
        assert isinstance(client, OpenLibraryClient)

    def test_created_via_factory_alias_books(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("books")
        assert isinstance(client, OpenLibraryClient)


# ---------------------------------------------------------------------------
# search_books()
# ---------------------------------------------------------------------------

class TestOpenLibrarySearchBooks:
    @resp_lib.activate
    def test_search_returns_dict_with_books(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/search.json",
            json=OPENLIBRARY_SEARCH_RESPONSE,
            status=200,
        )
        result = openlibrary_client.search_books("Hitchhiker's Guide")
        assert "books" in result
        assert "num_found" in result
        assert result["num_found"] == 1

    @resp_lib.activate
    def test_search_book_has_required_fields(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/search.json",
            json=OPENLIBRARY_SEARCH_RESPONSE,
            status=200,
        )
        result = openlibrary_client.search_books("Hitchhiker's Guide")
        book = result["books"][0]
        for key in ("title", "author", "first_publish_year", "isbn", "key"):
            assert key in book

    @resp_lib.activate
    def test_search_book_data_matches_response(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/search.json",
            json=OPENLIBRARY_SEARCH_RESPONSE,
            status=200,
        )
        result = openlibrary_client.search_books("Hitchhiker's Guide")
        book = result["books"][0]
        assert book["title"] == "The Hitchhiker's Guide to the Galaxy"
        assert "Douglas Adams" in book["author"]
        assert book["first_publish_year"] == 1979

    @resp_lib.activate
    def test_search_subjects_limited_to_five(self, openlibrary_client):
        doc = dict(OPENLIBRARY_SEARCH_RESPONSE["docs"][0])
        doc["subject"] = [f"Subject {i}" for i in range(10)]
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/search.json",
            json={"numFound": 1, "docs": [doc]},
            status=200,
        )
        result = openlibrary_client.search_books("test")
        assert len(result["books"][0]["subject"]) <= 5

    @resp_lib.activate
    def test_search_empty_results(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/search.json",
            json={"numFound": 0, "docs": []},
            status=200,
        )
        result = openlibrary_client.search_books("xyzzy not a book")
        assert result["books"] == []
        assert result["num_found"] == 0

    @resp_lib.activate
    def test_search_network_error_returns_error_dict(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/search.json",
            body=ConnectionError("refused"),
        )
        result = openlibrary_client.search_books("Python")
        assert "error" in result

    @resp_lib.activate
    def test_search_query_in_request(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/search.json",
            json=OPENLIBRARY_SEARCH_RESPONSE,
            status=200,
        )
        openlibrary_client.search_books("Dune", limit=5)
        req_url = resp_lib.calls[0].request.url
        assert "Dune" in req_url
        assert "limit=5" in req_url


# ---------------------------------------------------------------------------
# get_book_by_isbn()
# ---------------------------------------------------------------------------

class TestOpenLibraryGetBookByIsbn:
    ISBN = "0345391802"

    @resp_lib.activate
    def test_get_book_by_isbn_returns_dict(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/api/books",
            json=OPENLIBRARY_ISBN_RESPONSE,
            status=200,
        )
        result = openlibrary_client.get_book_by_isbn(self.ISBN)
        assert "title" in result
        assert "authors" in result

    @resp_lib.activate
    def test_get_book_by_isbn_has_correct_title(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/api/books",
            json=OPENLIBRARY_ISBN_RESPONSE,
            status=200,
        )
        result = openlibrary_client.get_book_by_isbn(self.ISBN)
        assert result["title"] == "The Hitchhiker's Guide to the Galaxy"
        assert "Douglas Adams" in result["authors"]

    @resp_lib.activate
    def test_get_book_by_isbn_has_all_fields(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/api/books",
            json=OPENLIBRARY_ISBN_RESPONSE,
            status=200,
        )
        result = openlibrary_client.get_book_by_isbn(self.ISBN)
        for key in ("title", "authors", "publish_date", "publishers",
                    "number_of_pages", "subjects", "cover", "url"):
            assert key in result

    @resp_lib.activate
    def test_get_book_by_isbn_not_found_returns_error(self, openlibrary_client):
        resp_lib.add(resp_lib.GET, f"{OL_BASE}/api/books", json={}, status=200)
        result = openlibrary_client.get_book_by_isbn("0000000000")
        assert "error" in result

    @resp_lib.activate
    def test_get_book_by_isbn_network_error_returns_error(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/api/books",
            body=ConnectionError("timeout"),
        )
        result = openlibrary_client.get_book_by_isbn(self.ISBN)
        assert "error" in result


# ---------------------------------------------------------------------------
# get_author()
# ---------------------------------------------------------------------------

class TestOpenLibraryGetAuthor:
    AUTHOR_RESPONSE = {
        "name": "Douglas Adams",
        "birth_date": "11 March 1952",
        "death_date": "11 May 2001",
        "bio": {"type": "/type/text", "value": "English author and humorist."},
        "photos": [12345],
        "wikipedia": "https://en.wikipedia.org/wiki/Douglas_Adams",
        "key": "/authors/OL23919A",
    }

    @resp_lib.activate
    def test_get_author_returns_dict_with_name(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/authors/OL23919A.json",
            json=self.AUTHOR_RESPONSE,
            status=200,
        )
        result = openlibrary_client.get_author("/authors/OL23919A")
        assert result["name"] == "Douglas Adams"

    @resp_lib.activate
    def test_get_author_bio_extracted_from_dict(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/authors/OL23919A.json",
            json=self.AUTHOR_RESPONSE,
            status=200,
        )
        result = openlibrary_client.get_author("/authors/OL23919A")
        assert result["bio"] == "English author and humorist."

    @resp_lib.activate
    def test_get_author_adds_prefix_if_missing(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/authors/OL23919A.json",
            json=self.AUTHOR_RESPONSE,
            status=200,
        )
        # Should work without the leading /authors/ prefix
        result = openlibrary_client.get_author("OL23919A")
        assert result["name"] == "Douglas Adams"

    @resp_lib.activate
    def test_get_author_network_error_returns_error(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/authors/OL23919A.json",
            body=ConnectionError("refused"),
        )
        result = openlibrary_client.get_author("/authors/OL23919A")
        assert "error" in result


# ---------------------------------------------------------------------------
# get_subjects()
# ---------------------------------------------------------------------------

class TestOpenLibraryGetSubjects:
    SUBJECTS_RESPONSE = {
        "name": "science_fiction",
        "work_count": 5000,
        "works": [
            {
                "title": "Dune",
                "authors": [{"name": "Frank Herbert"}],
                "first_publish_year": 1965,
                "key": "/works/OL36599W",
                "cover_id": 12345,
            }
        ],
    }

    @resp_lib.activate
    def test_get_subjects_returns_books_list(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/subjects/science_fiction.json",
            json=self.SUBJECTS_RESPONSE,
            status=200,
        )
        result = openlibrary_client.get_subjects("science_fiction")
        assert "books" in result
        assert "work_count" in result
        assert result["work_count"] == 5000

    @resp_lib.activate
    def test_get_subjects_book_has_fields(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/subjects/science_fiction.json",
            json=self.SUBJECTS_RESPONSE,
            status=200,
        )
        result = openlibrary_client.get_subjects("science_fiction")
        book = result["books"][0]
        for key in ("title", "authors", "first_publish_year", "key"):
            assert key in book

    @resp_lib.activate
    def test_get_subjects_network_error_returns_error(self, openlibrary_client):
        resp_lib.add(
            resp_lib.GET, f"{OL_BASE}/subjects/science_fiction.json",
            body=ConnectionError("refused"),
        )
        result = openlibrary_client.get_subjects("science_fiction")
        assert "error" in result
