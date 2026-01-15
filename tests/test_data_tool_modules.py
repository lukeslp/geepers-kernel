from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import sys
import types

import pytest

SHARED_DIR = Path(__file__).resolve().parents[1]
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

pandas_stub = types.ModuleType("pandas")
pandas_stub.DataFrame = object
pandas_stub.Series = object


def _not_implemented(*_args, **_kwargs):
    raise NotImplementedError("Stub pandas module does not implement this function")

pandas_stub.to_numeric = _not_implemented
pandas_stub.read_csv = _not_implemented

sys.modules.setdefault("pandas", pandas_stub)

arxiv_stub = types.ModuleType("arxiv")


class _StubClient:
    def __init__(self, *args, **kwargs):
        pass

    def results(self, *_args, **_kwargs):
        return []


class _StubSearch:
    def __init__(self, *args, **kwargs):
        pass


class _StubSortCriterion:
    Relevance = "relevance"
    LastUpdatedDate = "last_updated"


arxiv_stub.Client = _StubClient
arxiv_stub.Search = _StubSearch
arxiv_stub.SortCriterion = _StubSortCriterion

sys.modules.setdefault("arxiv", arxiv_stub)

from shared.tools import data_tool_base
from shared.tools.archive_tool import ArchiveTools
from shared.tools.arxiv_tool import ArxivTools
from shared.tools.census_tool import CensusTools
from shared.tools.finance_tool import FinanceTools
from shared.tools.github_tool import GitHubTools
from shared.tools.youtube_tool import YouTubeTools


@pytest.fixture
def factory_registry(monkeypatch):
    registry: Dict[str, Any] = {}

    def fake_create_client(source: str, **kwargs):
        if source not in registry:
            raise AssertionError(f"Unexpected data source requested: {source}")
        client = registry[source]
        # Record kwargs for assertions if the stub supports it
        setattr(client, "_last_kwargs", kwargs)
        return client

    monkeypatch.setattr(
        data_tool_base.DataFetchingFactory,
        "create_client",
        staticmethod(fake_create_client),
    )

    return registry


class FakeDataFrame:
    """Simple stand-in for pandas DataFrame used by Census client."""

    def __init__(self, records: List[Dict[str, Any]]):
        self._records = records

    def to_dict(self, orient: str = "records"):
        assert orient == "records"
        return list(self._records)


def test_census_tools_fetch_and_limit(factory_registry):
    class StubCensus:
        def __init__(self):
            self.fetch_calls: List[Dict[str, Any]] = []

        def fetch_acs(self, **kwargs):
            self.fetch_calls.append(kwargs)
            return FakeDataFrame(
                [
                    {"name": "County A", "population": 1000},
                    {"name": "County B", "population": 500},
                    {"name": "County C", "population": 250},
                ]
            )

        def fetch_population(self, **kwargs):
            return FakeDataFrame(
                [
                    {"name": "Oregon", "population": 4200000},
                    {"name": "Washington", "population": 7600000},
                ]
            )

        def get_metadata(self):
            return {"source": "stub"}

    stub = StubCensus()
    factory_registry["census"] = stub

    tool = CensusTools()

    acs_result = tool.census_fetch_acs(
        year=2024,
        variables={"B01003_001E": "population"},
        geography="county:*",
        dataset="acs5",
        limit=2,
    )

    assert acs_result["year"] == 2024
    assert len(acs_result["records"]) == 2
    assert acs_result["metadata"]["source"] == "stub"
    assert stub.fetch_calls, "Expected Census fetch to be invoked"

    population_result = tool.census_fetch_population(year=2023, geography="state", limit=1)
    assert len(population_result["records"]) == 1
    # Confirm client reuse (only one client instance created)
    assert tool._client is stub  # type: ignore[attr-defined]


def test_arxiv_tools_convert_papers(factory_registry):
    @dataclass
    class StubPaper:
        title: str

        def to_dict(self):
            return {"title": self.title}

    class StubArxiv:
        def search(self, query: str, max_results: int, sort_by: str = "relevance"):
            assert query
            assert max_results <= 25
            return [StubPaper("Paper One"), StubPaper("Paper Two")]

        def get_by_id(self, paper_id: str):
            return None

    factory_registry["arxiv"] = StubArxiv()

    tool = ArxivTools()
    result = tool.arxiv_search(query="quantum", max_results=50)
    assert result["count"] == 2
    assert result["papers"][0]["title"] == "Paper One"

    missing = tool.arxiv_get_paper("1234")
    assert "error" in missing


def test_github_tools_apply_limits(factory_registry):
    class StubGitHub:
        def search_repositories(self, **kwargs):
            assert kwargs["per_page"] <= 50
            return {"repositories": [{"name": "repo1"}, {"name": "repo2"}]}

        def search_code(self, **kwargs):
            assert kwargs["per_page"] <= 50
            return {"results": [{"path": "main.py"}, {"path": "utils.py"}]}

        def search_issues(self, **kwargs):
            return {"items": [{"title": "bug"}, {"title": "feature"}]}

        def get_repository(self, owner: str, repo: str):
            return {"name": f"{owner}/{repo}"}

    factory_registry["github"] = StubGitHub()
    tool = GitHubTools()

    repo_result = tool.github_search_repositories(query="ml", per_page=100)
    assert len(repo_result["repositories"]) == 2

    code_result = tool.github_search_code(query="torch", per_page=100)
    assert len(code_result["results"]) == 2

    issue_result = tool.github_search_issues(query="bug")
    assert issue_result["items"][0]["title"] == "bug"

    repo_detail = tool.github_get_repository(owner="coolhand", repo="shared")
    assert repo_detail["name"] == "coolhand/shared"


def test_archive_tools_snapshot_conversion(factory_registry):
    @dataclass
    class Snapshot:
        url: str
        archive_url: str
        timestamp: Any
        status_code: int
        original_url: str

    class StubArchive:
        def get_latest_snapshot(self, url: str):
            return Snapshot(
                url=url,
                archive_url="https://web.archive.org/web/123/example",
                timestamp=datetime(2024, 1, 1),
                status_code=200,
                original_url=url,
            )

        def get_all_snapshots(self, url: str, limit: int = 25):
            return [
                Snapshot(
                    url=url,
                    archive_url=f"https://web.archive.org/web/{idx}/example",
                    timestamp=datetime(2023, 1, idx + 1),
                    status_code=200,
                    original_url=url,
                )
                for idx in range(3)
            ]

        def archive_url(self, url: str, wait_for_completion: bool, retry_delay: int):
            return type("Result", (), {"success": True, "archive_url": "https://web/archive", "error": None, "snapshot": None})()

    factory_registry["archive"] = StubArchive()
    tool = ArchiveTools()

    latest = tool.archive_get_latest_snapshot("https://example.com")
    assert latest["snapshot"]["archive_url"].startswith("https://web.archive.org")

    snapshots = tool.archive_list_snapshots("https://example.com", limit=2)
    assert snapshots["count"] == 2

    archive_result = tool.archive_url("https://example.com", wait_for_completion=False)
    assert archive_result["success"] is True


def test_finance_tools_trim_results(factory_registry):
    class StubFinance:
        def get_daily_time_series(self, symbol: str, output_size: str = "compact"):
            return {"metadata": {}, "prices": [{"date": "2024-01-01"}, {"date": "2024-01-02"}]}

        def get_fx_rate(self, from_currency: str, to_currency: str):
            return {"pair": f"{from_currency}/{to_currency}", "exchange_rate": 1.1}

        def get_crypto_quote(self, symbol: str, market: str = "USD"):
            return {"metadata": {}, "quotes": [{"date": "2024-01-01"}, {"date": "2024-01-02"}]}

    factory_registry["finance"] = StubFinance()
    tool = FinanceTools()

    time_series = tool.finance_daily_time_series(symbol="AAPL", output_size="full")
    assert len(time_series["prices"]) == 2
    assert time_series["symbol"] == "AAPL"

    fx = tool.finance_fx_rate(from_currency="USD", to_currency="EUR")
    assert fx["pair"] == "USD/EUR"

    crypto = tool.finance_crypto_quote(symbol="BTC", market="USD")
    assert len(crypto["quotes"]) == 2


def test_youtube_tools_pass_through(factory_registry):
    class StubYouTube:
        def search_videos(self, **kwargs):
            assert kwargs["max_results"] <= 25
            return {"videos": [{"video_id": "abc"}]}

        def get_channel_statistics(self, channel_id: str):
            return {"channel_id": channel_id, "view_count": 100}

        def get_playlist_items(self, playlist_id: str, max_results: int):
            return {"items": [{"video_id": "xyz"}]}

    factory_registry["youtube"] = StubYouTube()
    tool = YouTubeTools()

    videos = tool.youtube_search_videos(query="music", max_results=50)
    assert videos["videos"][0]["video_id"] == "abc"

    channel = tool.youtube_channel_statistics(channel_id="UC123")
    assert channel["view_count"] == 100

    playlist = tool.youtube_playlist_items(playlist_id="PL123", max_results=30)
    assert playlist["items"]

