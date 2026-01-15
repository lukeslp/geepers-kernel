"""
Tool module for GitHub REST API access.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .data_tool_base import DataToolModuleBase


class GitHubTools(DataToolModuleBase):
    """Expose GitHub repository, code, and issue search through the tool registry."""

    name = "github_data"
    display_name = "GitHub Search"
    description = "Search repositories, code, and issues using the GitHub API"
    version = "1.0.0"
    source_name = "github"
    api_key_name = "github"
    max_records = 50

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "github_search_repositories",
                    "description": "Search GitHub repositories by query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query."},
                            "sort": {
                                "type": "string",
                                "default": "stars",
                                "description": "Sort field (stars, forks, updated).",
                            },
                            "order": {
                                "type": "string",
                                "default": "desc",
                                "description": "Sort order (asc or desc).",
                            },
                            "per_page": {
                                "type": "integer",
                                "default": 30,
                                "description": "Maximum number of results (<=50).",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "github_search_code",
                    "description": "Search GitHub code snippets.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Code search query."},
                            "per_page": {
                                "type": "integer",
                                "default": 30,
                                "description": "Maximum number of results (<=50).",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "github_search_issues",
                    "description": "Search GitHub issues and pull requests.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Issue search query."},
                            "sort": {
                                "type": "string",
                                "default": "created",
                                "description": "Sort field (created, updated, comments).",
                            },
                            "order": {
                                "type": "string",
                                "default": "desc",
                                "description": "Sort order (asc or desc).",
                            },
                            "per_page": {
                                "type": "integer",
                                "default": 30,
                                "description": "Maximum number of results (<=50).",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "github_get_repository",
                    "description": "Retrieve repository details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "owner": {"type": "string", "description": "Repository owner."},
                            "repo": {"type": "string", "description": "Repository name."},
                        },
                        "required": ["owner", "repo"],
                    },
                },
            },
        ]

    def github_search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 30,
    ) -> Dict[str, Any]:
        """Search GitHub repositories and return capped results."""
        client = self._get_client()
        per_page = min(per_page, self.max_records or per_page)
        result = client.search_repositories(query=query, sort=sort, order=order, per_page=per_page)
        repositories = result.get("repositories", [])
        result["repositories"] = self._apply_record_limit(repositories)
        result["query"] = query
        return result

    def github_search_code(self, query: str, per_page: int = 30) -> Dict[str, Any]:
        """Search code on GitHub."""
        client = self._get_client()
        per_page = min(per_page, self.max_records or per_page)
        result = client.search_code(query=query, per_page=per_page)
        result["results"] = self._apply_record_limit(result.get("results", []))
        result["query"] = query
        return result

    def github_search_issues(
        self,
        query: str,
        sort: str = "created",
        order: str = "desc",
        per_page: int = 30,
    ) -> Dict[str, Any]:
        """Search issues and pull requests."""
        client = self._get_client()
        per_page = min(per_page, self.max_records or per_page)
        result = client.search_issues(query=query, sort=sort, order=order, per_page=per_page)
        result["items"] = self._apply_record_limit(result.get("items", []))
        result["query"] = query
        return result

    def github_get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Retrieve a repository by owner/name."""
        client = self._get_client()
        data = client.get_repository(owner=owner, repo=repo)
        data["owner"] = owner
        data["repo"] = repo
        return data


if __name__ == "__main__":
    GitHubTools.main()

