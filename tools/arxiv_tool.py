"""
Tool module for interacting with the arXiv API.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .data_tool_base import DataToolModuleBase


class ArxivTools(DataToolModuleBase):
    """Expose arXiv search capabilities as tools."""

    name = "arxiv_data"
    display_name = "arXiv Research"
    description = "Search and retrieve scientific papers from arXiv."
    version = "1.0.0"
    source_name = "arxiv"
    api_key_name = None
    max_records = 25

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "arxiv_search",
                    "description": "Search arXiv for papers matching a query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query string."},
                            "max_results": {
                                "type": "integer",
                                "default": 5,
                                "description": "Maximum number of results (<=25).",
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["relevance", "date"],
                                "default": "relevance",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "arxiv_get_paper",
                    "description": "Retrieve metadata for a paper by arXiv ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "paper_id": {
                                "type": "string",
                                "description": "arXiv identifier (e.g., 2301.07041).",
                            }
                        },
                        "required": ["paper_id"],
                    },
                },
            },
        ]

    def arxiv_search(
        self,
        query: str,
        max_results: int = 5,
        sort_by: str = "relevance",
    ) -> Dict[str, Any]:
        """Search arXiv and return simplified paper metadata."""
        client = self._get_client()
        results = client.search(query=query, max_results=min(max_results, self.max_records), sort_by=sort_by)
        papers = [paper.to_dict() for paper in results]
        return {"query": query, "papers": papers, "count": len(papers)}

    def arxiv_get_paper(self, paper_id: str) -> Dict[str, Any]:
        """Retrieve a paper by ID."""
        client = self._get_client()
        paper = client.get_by_id(paper_id)
        if not paper:
            return {"error": f"Paper not found for id {paper_id}"}
        return paper.to_dict()


if __name__ == "__main__":
    ArxivTools.main()

