"""
Tool module for Semantic Scholar academic research API.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .data_tool_base import DataToolModuleBase


class SemanticScholarTools(DataToolModuleBase):
    """Expose Semantic Scholar search and retrieval operations as tools."""

    name = "semantic_scholar_data"
    display_name = "Semantic Scholar"
    description = "Search academic papers and retrieve metadata from Semantic Scholar"
    version = "1.0.0"
    source_name = "semantic_scholar"
    api_key_name = None
    max_records = 25

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "semantic_scholar_search",
                    "description": "Search Semantic Scholar for papers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query string."},
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
                    "name": "semantic_scholar_get_paper",
                    "description": "Retrieve a paper by DOI.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doi": {"type": "string", "description": "Digital Object Identifier."}
                        },
                        "required": ["doi"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "semantic_scholar_search_author",
                    "description": "Search Semantic Scholar for papers by an author.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "author": {"type": "string", "description": "Author name."},
                            "limit": {
                                "type": "integer",
                                "default": 10,
                                "description": "Maximum number of results (<=25).",
                            },
                        },
                        "required": ["author"],
                    },
                },
            },
        ]

    @staticmethod
    def _papers_to_dict(papers: List[Any]) -> List[Dict[str, Any]]:
        """Convert SemanticScholarPaper objects to dictionaries."""
        serialised: List[Dict[str, Any]] = []
        for paper in papers:
            if hasattr(paper, "to_dict"):
                serialised.append(paper.to_dict())
        return serialised

    def semantic_scholar_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search Semantic Scholar for papers."""
        client = self._get_client()
        papers = client.search(query=query, limit=min(limit, self.max_records or limit))
        return {
            "query": query,
            "papers": self._papers_to_dict(papers),
            "count": len(papers),
        }

    def semantic_scholar_get_paper(self, doi: str) -> Dict[str, Any]:
        """Retrieve paper metadata by DOI."""
        client = self._get_client()
        paper = client.get_by_doi(doi)
        if paper is None:
            return {"error": f"Paper not found for doi {doi}", "doi": doi}
        return paper.to_dict()

    def semantic_scholar_search_author(self, author: str, limit: int = 10) -> Dict[str, Any]:
        """Search for papers by author name."""
        client = self._get_client()
        query = f'au:"{author}"'
        papers = client.search(query=query, limit=min(limit, self.max_records or limit))
        return {
            "author": author,
            "papers": self._papers_to_dict(papers),
            "count": len(papers),
        }


if __name__ == "__main__":
    SemanticScholarTools.main()

