"""
Tests for GitHubClient.

All HTTP calls are intercepted with the `responses` library.
"""

import pytest
import responses as resp_lib
from requests.exceptions import ConnectionError

from research_data_clients import GitHubClient
from tests.conftest import GITHUB_REPO_SEARCH_RESPONSE, GITHUB_REPO_RESPONSE


GH_BASE = "https://api.github.com"


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestGitHubClientInit:
    def test_no_api_key_still_creates_client(self):
        import os
        # Ensure env vars not set for this test
        env_backup = {k: os.environ.pop(k, None) for k in ("GITHUB_TOKEN", "GITHUB_API_KEY")}
        try:
            client = GitHubClient()
            assert client.api_key is None
        finally:
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v

    def test_api_key_sets_auth_header(self, github_client):
        auth = github_client.session.headers.get("Authorization", "")
        assert "Bearer" in auth
        assert "fake-token-for-tests" in auth

    def test_created_via_factory(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("github")
        assert isinstance(client, GitHubClient)

    def test_created_via_factory_with_key(self):
        from research_data_clients import ClientFactory
        client = ClientFactory.create_client("github", api_key="gh-pat")
        assert client.api_key == "gh-pat"


# ---------------------------------------------------------------------------
# search_repositories()
# ---------------------------------------------------------------------------

class TestGitHubSearchRepositories:
    @resp_lib.activate
    def test_search_returns_dict_with_repositories(self, github_client):
        resp_lib.add(
            resp_lib.GET, f"{GH_BASE}/search/repositories",
            json=GITHUB_REPO_SEARCH_RESPONSE,
            status=200,
        )
        result = github_client.search_repositories("requests language:python")
        assert "repositories" in result
        assert "total_count" in result
        assert result["total_count"] == 1

    @resp_lib.activate
    def test_search_repo_has_required_fields(self, github_client):
        resp_lib.add(
            resp_lib.GET, f"{GH_BASE}/search/repositories",
            json=GITHUB_REPO_SEARCH_RESPONSE,
            status=200,
        )
        result = github_client.search_repositories("requests")
        repo = result["repositories"][0]
        for key in ("name", "description", "stars", "forks", "language", "url"):
            assert key in repo

    @resp_lib.activate
    def test_search_repo_data_matches_response(self, github_client):
        resp_lib.add(
            resp_lib.GET, f"{GH_BASE}/search/repositories",
            json=GITHUB_REPO_SEARCH_RESPONSE,
            status=200,
        )
        result = github_client.search_repositories("requests")
        repo = result["repositories"][0]
        assert repo["name"] == "psf/requests"
        assert repo["stars"] == 50000
        assert repo["language"] == "Python"

    @resp_lib.activate
    def test_search_repo_network_error_returns_error_dict(self, github_client):
        resp_lib.add(
            resp_lib.GET, f"{GH_BASE}/search/repositories",
            body=ConnectionError("refused"),
        )
        result = github_client.search_repositories("test")
        assert "error" in result

    @resp_lib.activate
    def test_search_repo_http_403_returns_error_dict(self, github_client):
        resp_lib.add(resp_lib.GET, f"{GH_BASE}/search/repositories", status=403)
        result = github_client.search_repositories("test")
        assert "error" in result

    @resp_lib.activate
    def test_search_repo_sends_sort_and_order(self, github_client):
        resp_lib.add(
            resp_lib.GET, f"{GH_BASE}/search/repositories",
            json=GITHUB_REPO_SEARCH_RESPONSE,
            status=200,
        )
        github_client.search_repositories("test", sort="forks", order="asc")
        req_url = resp_lib.calls[0].request.url
        assert "sort=forks" in req_url
        assert "order=asc" in req_url


# ---------------------------------------------------------------------------
# get_repository()
# ---------------------------------------------------------------------------

class TestGitHubGetRepository:
    @resp_lib.activate
    def test_get_repo_returns_dict_with_fields(self, github_client):
        resp_lib.add(
            resp_lib.GET, f"{GH_BASE}/repos/psf/requests",
            json=GITHUB_REPO_RESPONSE,
            status=200,
        )
        result = github_client.get_repository("psf", "requests")
        for key in ("name", "description", "stars", "forks", "language",
                    "topics", "url", "created_at", "updated_at"):
            assert key in result

    @resp_lib.activate
    def test_get_repo_data_matches_response(self, github_client):
        resp_lib.add(
            resp_lib.GET, f"{GH_BASE}/repos/psf/requests",
            json=GITHUB_REPO_RESPONSE,
            status=200,
        )
        result = github_client.get_repository("psf", "requests")
        assert result["name"] == "psf/requests"
        assert result["stars"] == 50000
        assert result["license"] == "Apache 2.0"

    @resp_lib.activate
    def test_get_repo_topics_is_list(self, github_client):
        resp_lib.add(
            resp_lib.GET, f"{GH_BASE}/repos/psf/requests",
            json=GITHUB_REPO_RESPONSE,
            status=200,
        )
        result = github_client.get_repository("psf", "requests")
        assert isinstance(result["topics"], list)

    @resp_lib.activate
    def test_get_repo_404_returns_error_dict(self, github_client):
        resp_lib.add(resp_lib.GET, f"{GH_BASE}/repos/nobody/nothing", status=404)
        result = github_client.get_repository("nobody", "nothing")
        assert "error" in result

    @resp_lib.activate
    def test_get_repo_network_error_returns_error_dict(self, github_client):
        resp_lib.add(
            resp_lib.GET, f"{GH_BASE}/repos/psf/requests",
            body=ConnectionError("timeout"),
        )
        result = github_client.get_repository("psf", "requests")
        assert "error" in result


# ---------------------------------------------------------------------------
# search_issues()
# ---------------------------------------------------------------------------

class TestGitHubSearchIssues:
    @resp_lib.activate
    def test_search_issues_returns_dict(self, github_client):
        payload = {
            "total_count": 1,
            "items": [
                {
                    "title": "Bug in requests",
                    "number": 1234,
                    "state": "open",
                    "user": {"login": "alice"},
                    "repository_url": "https://api.github.com/repos/psf/requests",
                    "created_at": "2024-01-01T00:00:00Z",
                    "html_url": "https://github.com/psf/requests/issues/1234",
                    "labels": [{"name": "bug"}],
                }
            ],
        }
        resp_lib.add(resp_lib.GET, f"{GH_BASE}/search/issues", json=payload, status=200)
        result = github_client.search_issues("bug repo:psf/requests")
        assert "issues" in result
        assert result["total_count"] == 1

    @resp_lib.activate
    def test_search_issues_issue_has_fields(self, github_client):
        payload = {
            "total_count": 1,
            "items": [
                {
                    "title": "Bug",
                    "number": 1,
                    "state": "open",
                    "user": {"login": "alice"},
                    "repository_url": "https://api.github.com/repos/psf/requests",
                    "created_at": "2024-01-01T00:00:00Z",
                    "html_url": "https://github.com/psf/requests/issues/1",
                    "labels": [],
                }
            ],
        }
        resp_lib.add(resp_lib.GET, f"{GH_BASE}/search/issues", json=payload, status=200)
        result = github_client.search_issues("bug")
        issue = result["issues"][0]
        for key in ("title", "number", "state", "user", "url"):
            assert key in issue

    @resp_lib.activate
    def test_search_issues_error_returns_error_dict(self, github_client):
        resp_lib.add(resp_lib.GET, f"{GH_BASE}/search/issues", status=422)
        result = github_client.search_issues("bad query ::")
        assert "error" in result


# ---------------------------------------------------------------------------
# search_code()
# ---------------------------------------------------------------------------

class TestGitHubSearchCode:
    @resp_lib.activate
    def test_search_code_returns_dict(self, github_client):
        payload = {
            "total_count": 1,
            "items": [
                {
                    "name": "session.py",
                    "path": "requests/session.py",
                    "repository": {"full_name": "psf/requests"},
                    "html_url": "https://github.com/psf/requests/blob/main/requests/session.py",
                    "language": "Python",
                }
            ],
        }
        resp_lib.add(resp_lib.GET, f"{GH_BASE}/search/code", json=payload, status=200)
        result = github_client.search_code("Session language:python repo:psf/requests")
        assert "results" in result
        assert result["total_count"] == 1

    @resp_lib.activate
    def test_search_code_result_has_fields(self, github_client):
        payload = {
            "total_count": 1,
            "items": [
                {
                    "name": "session.py",
                    "path": "requests/session.py",
                    "repository": {"full_name": "psf/requests"},
                    "html_url": "https://github.com/psf/requests/blob/main/requests/session.py",
                    "language": "Python",
                }
            ],
        }
        resp_lib.add(resp_lib.GET, f"{GH_BASE}/search/code", json=payload, status=200)
        result = github_client.search_code("Session")
        item = result["results"][0]
        for key in ("name", "path", "repository", "url"):
            assert key in item
