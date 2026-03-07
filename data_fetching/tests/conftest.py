"""
Shared fixtures and mock response data for research-data-clients tests.

All HTTP calls are intercepted - no real network requests are made.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Realistic mock payload shapes
# ---------------------------------------------------------------------------

WIKIPEDIA_OPENSEARCH_RESPONSE = [
    "Python",
    ["Python (programming language)", "Python (snake)", "Monty Python"],
    [
        "Python is a high-level, general-purpose programming language.",
        "Pythons are large snakes.",
        "Monty Python was a British comedy group.",
    ],
    [
        "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "https://en.wikipedia.org/wiki/Python_(snake)",
        "https://en.wikipedia.org/wiki/Monty_Python",
    ],
]

WIKIPEDIA_SUMMARY_RESPONSE = {
    "query": {
        "pages": {
            "23862": {
                "pageid": 23862,
                "title": "Python (programming language)",
                "extract": "Python is a high-level, general-purpose programming language.",
                "original": {"source": "https://upload.wikimedia.org/python-logo.png"},
            }
        }
    }
}

WIKIPEDIA_RANDOM_RESPONSE = {
    "query": {
        "random": [
            {"id": 55555, "title": "Banjo"},
        ]
    }
}

PUBMED_SEARCH_RESPONSE = {
    "esearchresult": {
        "count": "2",
        "retmax": "10",
        "idlist": ["38000001", "38000002"],
    }
}

PUBMED_SUMMARY_RESPONSE = {
    "result": {
        "uids": ["38000001", "38000002"],
        "38000001": {
            "uid": "38000001",
            "title": "CRISPR-Cas9 genome editing: mechanisms and applications",
            "authors": [{"name": "Smith J"}, {"name": "Jones A"}],
            "fulljournalname": "Nature Biotechnology",
            "pubdate": "2024",
            "elocationid": "doi: 10.1038/nbt.example",
            "pubtype": ["Journal Article", "Review"],
            "keywords": ["CRISPR", "genome editing"],
        },
        "38000002": {
            "uid": "38000002",
            "title": "Off-target effects of CRISPR editing",
            "authors": [{"name": "Brown K"}],
            "fulljournalname": "Cell",
            "pubdate": "2023",
            "elocationid": "",
            "pubtype": ["Journal Article"],
            "keywords": [],
        },
    }
}

PUBMED_SINGLE_SUMMARY_RESPONSE = {
    "result": {
        "uids": ["38000001"],
        "38000001": PUBMED_SUMMARY_RESPONSE["result"]["38000001"],
    }
}

SEMANTIC_SCHOLAR_SEARCH_RESPONSE = {
    "data": [
        {
            "paperId": "abc123",
            "title": "Attention Is All You Need",
            "authors": [{"name": "Vaswani A"}, {"name": "Shazeer N"}],
            "year": 2017,
            "abstract": "We propose the Transformer architecture.",
            "doi": "10.48550/arXiv.1706.03762",
            "venue": "NeurIPS",
            "url": "https://www.semanticscholar.org/paper/abc123",
            "citationCount": 80000,
            "referenceCount": 42,
            "influentialCitationCount": 5000,
            "topics": [{"topic": "Transformers"}, {"topic": "Attention"}],
        }
    ]
}

SEMANTIC_SCHOLAR_PAPER_RESPONSE = {
    "paperId": "abc123",
    "title": "Attention Is All You Need",
    "authors": [{"name": "Vaswani A"}],
    "year": 2017,
    "abstract": "We propose the Transformer architecture.",
    "doi": "10.48550/arXiv.1706.03762",
    "venue": "NeurIPS",
    "url": "https://www.semanticscholar.org/paper/abc123",
    "citationCount": 80000,
    "referenceCount": 42,
    "influentialCitationCount": 5000,
    "topics": [],
}

GITHUB_REPO_SEARCH_RESPONSE = {
    "total_count": 1,
    "items": [
        {
            "full_name": "psf/requests",
            "description": "A simple, yet elegant, HTTP library.",
            "stargazers_count": 50000,
            "forks_count": 9000,
            "language": "Python",
            "html_url": "https://github.com/psf/requests",
            "topics": ["http", "python"],
        }
    ],
}

GITHUB_REPO_RESPONSE = {
    "full_name": "psf/requests",
    "description": "A simple, yet elegant, HTTP library.",
    "stargazers_count": 50000,
    "forks_count": 9000,
    "watchers_count": 50000,
    "language": "Python",
    "topics": ["http", "python"],
    "created_at": "2011-02-13T18:38:17Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "html_url": "https://github.com/psf/requests",
    "homepage": "https://requests.readthedocs.io",
    "license": {"name": "Apache 2.0"},
}

OPENLIBRARY_SEARCH_RESPONSE = {
    "numFound": 1,
    "docs": [
        {
            "title": "The Hitchhiker's Guide to the Galaxy",
            "author_name": ["Douglas Adams"],
            "first_publish_year": 1979,
            "isbn": ["0345391802"],
            "publisher": ["Pan Books"],
            "language": ["eng"],
            "subject": ["Science fiction", "Humour"],
            "key": "/works/OL893415W",
            "cover_i": 8228691,
        }
    ],
}

OPENLIBRARY_ISBN_RESPONSE = {
    "ISBN:0345391802": {
        "title": "The Hitchhiker's Guide to the Galaxy",
        "authors": [{"name": "Douglas Adams"}],
        "publish_date": "October 12, 1979",
        "publishers": [{"name": "Pan Books"}],
        "number_of_pages": 193,
        "subjects": [{"name": "Science fiction"}],
        "cover": {"large": "https://covers.openlibrary.org/b/id/8228691-L.jpg"},
        "url": "https://openlibrary.org/books/OL7353617M",
    }
}

WAYBACK_AVAIL_RESPONSE = {
    "url": "https://example.com",
    "archived_snapshots": {
        "closest": {
            "status": "200",
            "available": True,
            "url": "https://web.archive.org/web/20231215120000/https://example.com",
            "timestamp": "20231215120000",
        }
    },
}

WAYBACK_AVAIL_EMPTY_RESPONSE = {
    "url": "https://notarchived.example.invalid",
    "archived_snapshots": {},
}


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def wikipedia_client():
    """Return a WikipediaClient instance."""
    from research_data_clients import WikipediaClient
    return WikipediaClient()


@pytest.fixture
def pubmed_client():
    """Return a PubMedClient instance (no API key)."""
    from research_data_clients import PubMedClient
    return PubMedClient()


@pytest.fixture
def pubmed_client_with_key():
    """Return a PubMedClient instance with an API key and email."""
    from research_data_clients import PubMedClient
    return PubMedClient(api_key="test-api-key", email="test@example.com")


@pytest.fixture
def semantic_scholar_client():
    """Return a SemanticScholarClient instance."""
    from research_data_clients import SemanticScholarClient
    return SemanticScholarClient()


@pytest.fixture
def github_client():
    """Return a GitHubClient with a fake token so auth header is set."""
    from research_data_clients import GitHubClient
    return GitHubClient(api_key="fake-token-for-tests")


@pytest.fixture
def openlibrary_client():
    """Return an OpenLibraryClient instance."""
    from research_data_clients import OpenLibraryClient
    return OpenLibraryClient()


@pytest.fixture
def archive_client():
    """Return an ArchiveClient instance."""
    from research_data_clients import ArchiveClient
    return ArchiveClient()


@pytest.fixture
def mock_arxiv_result():
    """Return a realistic mock arxiv.Result object."""
    result = MagicMock()
    result.title = "Attention Is All You Need"
    author1 = MagicMock()
    author1.name = "Vaswani A"
    author2 = MagicMock()
    author2.name = "Shazeer N"
    result.authors = [author1, author2]
    result.summary = "We propose the Transformer architecture."
    result.published = datetime(2017, 6, 12)
    result.updated = datetime(2017, 12, 6)
    result.entry_id = "https://arxiv.org/abs/1706.03762"
    result.pdf_url = "https://arxiv.org/pdf/1706.03762"
    result.categories = ["cs.CL", "cs.LG"]
    result.doi = None
    result.comment = "NeurIPS 2017"
    result.journal_ref = None
    result.primary_category = "cs.CL"
    return result
