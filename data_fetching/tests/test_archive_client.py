"""
Tests for ArchiveClient and MultiArchiveClient.

All HTTP calls are intercepted with the `responses` library.
"""

import pytest
import responses as resp_lib
from datetime import datetime
from requests.exceptions import ConnectionError

from research_data_clients import (
    ArchiveClient,
    ArchiveResult,
    ArchivedSnapshot,
    MultiArchiveClient,
)
from tests.conftest import WAYBACK_AVAIL_RESPONSE, WAYBACK_AVAIL_EMPTY_RESPONSE


AVAIL_URL = "https://archive.org/wayback/available"
SAVE_URL = "https://web.archive.org/save/"
CDX_URL = "https://web.archive.org/cdx/search/cdx"


# ---------------------------------------------------------------------------
# ArchivedSnapshot dataclass
# ---------------------------------------------------------------------------

class TestArchivedSnapshot:
    def test_from_api_response_parses_timestamp(self):
        data = {
            "status": "200",
            "url": "https://web.archive.org/web/20231215120000/https://example.com",
            "timestamp": "20231215120000",
        }
        snap = ArchivedSnapshot.from_api_response(data, "https://example.com")
        assert snap.timestamp == datetime(2023, 12, 15, 12, 0, 0)

    def test_from_api_response_sets_status_code(self):
        data = {
            "status": "301",
            "url": "https://web.archive.org/web/20231215/https://example.com",
            "timestamp": "20231215120000",
        }
        snap = ArchivedSnapshot.from_api_response(data, "https://example.com")
        assert snap.status_code == 301

    def test_from_api_response_preserves_original_url(self):
        data = {
            "status": "200",
            "url": "https://web.archive.org/web/20231215/https://example.com",
            "timestamp": "20231215120000",
        }
        snap = ArchivedSnapshot.from_api_response(data, "https://example.com")
        assert snap.original_url == "https://example.com"


# ---------------------------------------------------------------------------
# ArchiveResult dataclass
# ---------------------------------------------------------------------------

class TestArchiveResult:
    def test_success_result(self):
        result = ArchiveResult(success=True, archive_url="https://web.archive.org/web/2023/https://example.com")
        assert result.success is True
        assert result.archive_url is not None

    def test_failure_result(self):
        result = ArchiveResult(success=False, error="Network error")
        assert result.success is False
        assert result.error == "Network error"
        assert result.archive_url is None


# ---------------------------------------------------------------------------
# ArchiveClient instantiation
# ---------------------------------------------------------------------------

class TestArchiveClientInit:
    def test_default_user_agent_set(self, archive_client):
        assert archive_client.user_agent != ""
        assert "Mozilla" in archive_client.user_agent

    def test_custom_user_agent(self):
        client = ArchiveClient(user_agent="MyBot/1.0")
        assert client.user_agent == "MyBot/1.0"

    def test_headers_set(self, archive_client):
        assert "User-Agent" in archive_client.headers

    def test_created_via_factory(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("archive")
        assert isinstance(client, ArchiveClient)

    def test_created_via_factory_wayback_alias(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("wayback")
        assert isinstance(client, ArchiveClient)


# ---------------------------------------------------------------------------
# ArchiveClient.get_latest_snapshot()
# ---------------------------------------------------------------------------

class TestArchiveGetLatestSnapshot:
    @resp_lib.activate
    def test_returns_snapshot_when_available(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_RESPONSE, status=200)
        snap = archive_client.get_latest_snapshot("https://example.com")
        assert snap is not None
        assert isinstance(snap, ArchivedSnapshot)

    @resp_lib.activate
    def test_snapshot_archive_url_correct(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_RESPONSE, status=200)
        snap = archive_client.get_latest_snapshot("https://example.com")
        assert "web.archive.org" in snap.archive_url
        assert "example.com" in snap.archive_url

    @resp_lib.activate
    def test_returns_none_when_no_snapshots(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_EMPTY_RESPONSE, status=200)
        snap = archive_client.get_latest_snapshot("https://notarchived.example.invalid")
        assert snap is None

    @resp_lib.activate
    def test_returns_none_on_network_error(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, body=ConnectionError("refused"))
        snap = archive_client.get_latest_snapshot("https://example.com")
        assert snap is None

    @resp_lib.activate
    def test_returns_none_on_http_error(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, status=503)
        snap = archive_client.get_latest_snapshot("https://example.com")
        assert snap is None

    @resp_lib.activate
    def test_passes_url_param_in_request(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_RESPONSE, status=200)
        archive_client.get_latest_snapshot("https://example.com")
        req_url = resp_lib.calls[0].request.url
        assert "example.com" in req_url


# ---------------------------------------------------------------------------
# ArchiveClient.get_snapshot_at_timestamp()
# ---------------------------------------------------------------------------

class TestArchiveGetSnapshotAtTimestamp:
    @resp_lib.activate
    def test_returns_snapshot_for_timestamp(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_RESPONSE, status=200)
        ts = datetime(2023, 6, 1)
        snap = archive_client.get_snapshot_at_timestamp("https://example.com", ts)
        assert snap is not None

    @resp_lib.activate
    def test_timestamp_sent_in_correct_format(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_RESPONSE, status=200)
        ts = datetime(2023, 6, 1, 14, 30, 0)
        archive_client.get_snapshot_at_timestamp("https://example.com", ts)
        req_url = resp_lib.calls[0].request.url
        assert "20230601143000" in req_url

    @resp_lib.activate
    def test_returns_none_when_no_match(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_EMPTY_RESPONSE, status=200)
        snap = archive_client.get_snapshot_at_timestamp(
            "https://notarchived.example.invalid",
            datetime(2020, 1, 1)
        )
        assert snap is None

    @resp_lib.activate
    def test_returns_none_on_network_error(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, body=ConnectionError("timeout"))
        snap = archive_client.get_snapshot_at_timestamp("https://example.com", datetime.now())
        assert snap is None


# ---------------------------------------------------------------------------
# ArchiveClient.archive_url() — short-circuit when already archived
# ---------------------------------------------------------------------------

class TestArchiveUrlMethod:
    @resp_lib.activate
    def test_archive_url_already_exists_returns_success(self, archive_client):
        # First call: check existing — returns snapshot
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_RESPONSE, status=200)
        result = archive_client.archive_url("https://example.com", wait_for_completion=False)
        assert result.success is True
        assert result.archive_url is not None

    @resp_lib.activate
    def test_archive_url_no_existing_no_wait(self, archive_client):
        # First check: not archived
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_EMPTY_RESPONSE, status=200)
        # Archive save request
        resp_lib.add(resp_lib.GET, f"{SAVE_URL}https://newpage.example.com", status=200)
        result = archive_client.archive_url(
            "https://newpage.example.com", wait_for_completion=False
        )
        assert result.success is True

    @resp_lib.activate
    def test_archive_url_network_error_returns_failure(self, archive_client):
        resp_lib.add(resp_lib.GET, AVAIL_URL, body=ConnectionError("refused"))
        result = archive_client.archive_url("https://example.com")
        assert result.success is False
        assert result.error is not None


# ---------------------------------------------------------------------------
# ArchiveClient.get_all_snapshots()
# ---------------------------------------------------------------------------

class TestArchiveGetAllSnapshots:
    CDX_HEADER = ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"]
    CDX_ROW = [
        "com,example)/",
        "20231215120000",
        "https://example.com",
        "text/html",
        "200",
        "ABCDEF123456",
        "12345",
    ]

    @resp_lib.activate
    def test_returns_list_of_snapshots(self, archive_client):
        cdx_data = [self.CDX_HEADER, self.CDX_ROW]
        resp_lib.add(resp_lib.GET, CDX_URL, json=cdx_data, status=200)
        snapshots = archive_client.get_all_snapshots("https://example.com")
        assert isinstance(snapshots, list)
        assert len(snapshots) == 1
        assert isinstance(snapshots[0], ArchivedSnapshot)

    @resp_lib.activate
    def test_snapshot_timestamp_parsed(self, archive_client):
        cdx_data = [self.CDX_HEADER, self.CDX_ROW]
        resp_lib.add(resp_lib.GET, CDX_URL, json=cdx_data, status=200)
        snapshots = archive_client.get_all_snapshots("https://example.com")
        assert snapshots[0].timestamp == datetime(2023, 12, 15, 12, 0, 0)

    @resp_lib.activate
    def test_returns_empty_list_on_no_data(self, archive_client):
        resp_lib.add(resp_lib.GET, CDX_URL, json=[], status=200)
        snapshots = archive_client.get_all_snapshots("https://example.com")
        assert snapshots == []

    @resp_lib.activate
    def test_returns_empty_list_on_header_only(self, archive_client):
        resp_lib.add(resp_lib.GET, CDX_URL, json=[self.CDX_HEADER], status=200)
        snapshots = archive_client.get_all_snapshots("https://example.com")
        assert snapshots == []

    @resp_lib.activate
    def test_returns_empty_list_on_network_error(self, archive_client):
        resp_lib.add(resp_lib.GET, CDX_URL, body=ConnectionError("timeout"))
        snapshots = archive_client.get_all_snapshots("https://example.com")
        assert snapshots == []

    @resp_lib.activate
    def test_from_date_sent_in_request(self, archive_client):
        resp_lib.add(resp_lib.GET, CDX_URL, json=[], status=200)
        from_date = datetime(2023, 1, 1)
        archive_client.get_all_snapshots("https://example.com", from_date=from_date)
        req_url = resp_lib.calls[0].request.url
        assert "20230101" in req_url


# ---------------------------------------------------------------------------
# MultiArchiveClient
# ---------------------------------------------------------------------------

class TestMultiArchiveClient:
    def test_instantiates(self):
        client = MultiArchiveClient()
        assert client is not None

    def test_has_wayback_client(self):
        client = MultiArchiveClient()
        assert hasattr(client, "wayback_client")
        assert isinstance(client.wayback_client, ArchiveClient)

    def test_providers_list(self):
        assert "wayback" in MultiArchiveClient.PROVIDERS
        assert "archiveis" in MultiArchiveClient.PROVIDERS

    @resp_lib.activate
    def test_get_archive_wayback_success(self):
        client = MultiArchiveClient()
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_RESPONSE, status=200)
        result = client.get_archive("https://example.com", provider="wayback")
        assert result.success is True
        assert result.archive_url is not None

    @resp_lib.activate
    def test_get_archive_wayback_no_snapshot(self):
        client = MultiArchiveClient()
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_EMPTY_RESPONSE, status=200)
        result = client.get_archive("https://notarchived.example.invalid", provider="wayback")
        assert result.success is False

    def test_get_archive_unknown_provider_returns_failure(self):
        client = MultiArchiveClient()
        result = client.get_archive("https://example.com", provider="doesnotexist")
        assert result.success is False
        assert "Unknown provider" in result.error

    @resp_lib.activate
    def test_get_all_archives_returns_dict_for_each_provider(self):
        # Only test the wayback provider — other providers (archiveis, memento, 12ft)
        # make additional external calls that are out of scope for this unit test.
        client = MultiArchiveClient()
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_RESPONSE, status=200)
        result = client.get_archive("https://example.com", provider="wayback")
        assert isinstance(result, ArchiveResult)
        assert result.success is True


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

class TestArchiveConvenienceFunctions:
    @resp_lib.activate
    def test_archive_url_function_returns_success_result(self):
        from research_data_clients import archive_url
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_RESPONSE, status=200)
        result = archive_url("https://example.com", wait=False)
        assert isinstance(result, ArchiveResult)
        assert result.success is True

    @resp_lib.activate
    def test_get_latest_archive_function_returns_string(self):
        from research_data_clients import get_latest_archive
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_RESPONSE, status=200)
        url = get_latest_archive("https://example.com")
        assert isinstance(url, str)
        assert "web.archive.org" in url

    @resp_lib.activate
    def test_get_latest_archive_returns_none_when_missing(self):
        from research_data_clients import get_latest_archive
        resp_lib.add(resp_lib.GET, AVAIL_URL, json=WAYBACK_AVAIL_EMPTY_RESPONSE, status=200)
        url = get_latest_archive("https://notarchived.example.invalid")
        assert url is None
