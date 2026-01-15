"""
Tool module for OpenLibrary books and authors.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .data_tool_base import DataToolModuleBase


class OpenLibraryTools(DataToolModuleBase):
    """Expose OpenLibrary book, author, and subject data."""

    name = "openlibrary_data"
    display_name = "OpenLibrary"
    description = "Search books, retrieve ISBN metadata, and explore authors"
    version = "1.0.0"
    source_name = "openlibrary"
    api_key_name = None
    max_records = 50

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "openlibrary_search_books",
                    "description": "Search OpenLibrary for books.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query."},
                            "limit": {
                                "type": "integer",
                                "default": 10,
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
                    "name": "openlibrary_get_book",
                    "description": "Retrieve book details by ISBN.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "isbn": {"type": "string", "description": "ISBN identifier."}
                        },
                        "required": ["isbn"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "openlibrary_get_author",
                    "description": "Retrieve author metadata by author key.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "author_key": {
                                "type": "string",
                                "description": "OpenLibrary author key (e.g., OL23919A).",
                            }
                        },
                        "required": ["author_key"],
                    },
                },
            },
        ]

    def openlibrary_search_books(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search books on OpenLibrary."""
        client = self._get_client()
        result = client.search_books(query=query, limit=min(limit, self.max_records or limit))
        docs = result.get("docs", [])
        result["docs"] = self._apply_record_limit(docs)
        result["query"] = query
        return result

    def openlibrary_get_book(self, isbn: str) -> Dict[str, Any]:
        """Retrieve metadata for a book by ISBN."""
        client = self._get_client()
        result = client.get_book_by_isbn(isbn)
        result["isbn"] = isbn
        return result

    def openlibrary_get_author(self, author_key: str) -> Dict[str, Any]:
        """Retrieve information for a specific author."""
        client = self._get_client()
        result = client.get_author(author_key)
        result["author_key"] = author_key
        return result


if __name__ == "__main__":
    OpenLibraryTools.main()

