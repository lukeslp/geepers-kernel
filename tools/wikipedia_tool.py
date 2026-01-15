"""
Tool module for Wikipedia search and content retrieval.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .data_tool_base import DataToolModuleBase


class WikipediaTools(DataToolModuleBase):
    """Expose Wikipedia search and summary capabilities as registered tools."""

    name = "wikipedia_data"
    display_name = "Wikipedia"
    description = "Search Wikipedia and retrieve article content"
    version = "1.0.0"
    source_name = "wikipedia"
    api_key_name = None
    max_records = 25

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "wikipedia_search",
                    "description": "Search Wikipedia articles.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search keywords."},
                            "limit": {
                                "type": "integer",
                                "default": 10,
                                "description": "Maximum number of results (<=25).",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "wikipedia_get_summary",
                    "description": "Get a concise summary for a page title.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Article title."},
                        },
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "wikipedia_get_full_content",
                    "description": "Retrieve the full content for a page title.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Article title."},
                        },
                        "required": ["title"],
                    },
                },
            },
        ]

    def wikipedia_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search Wikipedia for matching pages."""
        client = self._get_client()
        result = client.search(query=query, limit=min(limit, self.max_records or limit))
        result["query"] = query
        search_results = result.get("results") or result.get("pages") or []
        result["results"] = self._apply_record_limit(search_results)
        return result

    def wikipedia_get_summary(self, title: str) -> Dict[str, Any]:
        """Retrieve the summary for a specific article."""
        client = self._get_client()
        summary = client.get_summary(title)
        summary["title"] = title
        return summary

    def wikipedia_get_full_content(self, title: str) -> Dict[str, Any]:
        """Retrieve full article content."""
        client = self._get_client()
        content = client.get_full_content(title)
        content["title"] = title
        return content


if __name__ == "__main__":
    WikipediaTools.main()

