"""
Tool module for aggregated news search via NewsAPI-compatible providers.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .data_tool_base import DataToolModuleBase


class NewsTools(DataToolModuleBase):
    """Expose news search, headlines, and source listings as tools."""

    name = "news_data"
    display_name = "News API"
    description = "Fetch top headlines, search news, and list news sources"
    version = "1.0.0"
    source_name = "news"
    api_key_name = "newsapi"
    max_records = 50

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "news_top_headlines",
                    "description": "Retrieve top headlines for a country or category.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "country": {
                                "type": "string",
                                "description": "ISO country code (e.g., us, gb).",
                            },
                            "category": {
                                "type": "string",
                                "description": "Optional category (business, technology, etc.).",
                            },
                            "query": {
                                "type": "string",
                                "description": "Optional search keywords.",
                            },
                            "page_size": {
                                "type": "integer",
                                "default": 20,
                                "description": "Max results (<=50).",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "news_search",
                    "description": "Search news articles across sources.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search keywords."},
                            "language": {
                                "type": "string",
                                "description": "Language code (default: en).",
                            },
                            "page_size": {
                                "type": "integer",
                                "default": 20,
                                "description": "Max results (<=50).",
                            },
                            "from_date": {
                                "type": "string",
                                "description": "ISO date for start of search window.",
                            },
                            "to_date": {
                                "type": "string",
                                "description": "ISO date for end of search window.",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "news_sources",
                    "description": "List news sources and metadata.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Filter by category.",
                            },
                            "language": {"type": "string", "description": "Filter by language."},
                            "country": {"type": "string", "description": "Filter by country."},
                        },
                    },
                },
            },
        ]

    def news_top_headlines(
        self,
        country: str = "us",
        category: str | None = None,
        query: str | None = None,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Retrieve top headlines."""
        client = self._get_client()
        page_size = min(page_size, self.max_records or page_size)
        result = client.get_top_headlines(
            country=country,
            category=category,
            query=query,
            page_size=page_size,
        )
        articles = result.get("articles", [])
        result["articles"] = self._apply_record_limit(articles)
        return result

    def news_search(
        self,
        query: str,
        language: str = "en",
        page_size: int = 20,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Dict[str, Any]:
        """Search across news sources."""
        client = self._get_client()
        page_size = min(page_size, self.max_records or page_size)
        result = client.search_everything(
            query=query,
            language=language,
            page_size=page_size,
            from_date=from_date,
            to_date=to_date,
        )
        result["articles"] = self._apply_record_limit(result.get("articles", []))
        result["query"] = query
        return result

    def news_sources(
        self,
        category: str | None = None,
        language: str | None = None,
        country: str | None = None,
    ) -> Dict[str, Any]:
        """List available news sources."""
        client = self._get_client()
        return client.get_sources(category=category, language=language, country=country)


if __name__ == "__main__":
    NewsTools.main()

