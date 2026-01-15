"""
Web Search Tool Module

Unified tool for web search across multiple providers:
- SerpAPI (Google Search)
- Tavily Search
- Brave Search

Author: Luke Steuber
"""

from typing import Dict, Any
import os
import requests

from .module_base import ToolModuleBase


class WebSearchTool(ToolModuleBase):
    """Web search across multiple providers."""

    name = "web_search"
    display_name = "Web Search"
    description = "Search the web using SerpAPI, Tavily, or Brave"
    version = "1.0.0"

    def initialize(self):
        """Initialize web search tool schemas."""
        # Check which API keys are available
        self.serp_key = os.getenv('SERP_API_KEY') or os.getenv('SERPAPI_API_KEY')
        self.tavily_key = os.getenv('TAVILY_API_KEY')
        self.brave_key = os.getenv('BRAVE_API_KEY')

        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web using available search providers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "provider": {
                                "type": "string",
                                "description": "Search provider to use",
                                "enum": ["serpapi", "tavily", "brave", "auto"],
                                "default": "auto"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Number of results to return",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def web_search(self, query: str, provider: str = "auto", num_results: int = 10) -> Dict[str, Any]:
        """
        Search the web using available providers.

        Args:
            query: Search query
            provider: Which provider to use (auto selects first available)
            num_results: Number of results

        Returns:
            Dict with search results
        """
        # Auto-select provider based on available keys
        if provider == "auto":
            if self.serp_key:
                provider = "serpapi"
            elif self.tavily_key:
                provider = "tavily"
            elif self.brave_key:
                provider = "brave"
            else:
                return {"error": "No web search API keys configured"}

        # Execute search
        if provider == "serpapi":
            return self._search_serpapi(query, num_results)
        elif provider == "tavily":
            return self._search_tavily(query, num_results)
        elif provider == "brave":
            return self._search_brave(query, num_results)
        else:
            return {"error": f"Unknown provider: {provider}"}

    def _search_serpapi(self, query: str, num_results: int) -> Dict[str, Any]:
        """Search using SerpAPI."""
        if not self.serp_key:
            return {"error": "SERP_API_KEY not configured"}

        try:
            response = requests.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": self.serp_key,
                    "num": num_results
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Extract organic results
            results = []
            for item in data.get('organic_results', [])[:num_results]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                    "position": item.get("position")
                })

            return {
                "query": query,
                "results": results,
                "count": len(results),
                "provider": "serpapi"
            }
        except Exception as e:
            return {"error": f"SerpAPI error: {str(e)}"}

    def _search_tavily(self, query: str, num_results: int) -> Dict[str, Any]:
        """Search using Tavily."""
        if not self.tavily_key:
            return {"error": "TAVILY_API_KEY not configured"}

        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_key,
                    "query": query,
                    "max_results": num_results
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get('results', []):
                results.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "snippet": item.get("content"),
                    "score": item.get("score")
                })

            return {
                "query": query,
                "results": results,
                "count": len(results),
                "provider": "tavily"
            }
        except Exception as e:
            return {"error": f"Tavily error: {str(e)}"}

    def _search_brave(self, query: str, num_results: int) -> Dict[str, Any]:
        """Search using Brave."""
        if not self.brave_key:
            return {"error": "BRAVE_API_KEY not configured"}

        try:
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": self.brave_key},
                params={"q": query, "count": num_results},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get('web', {}).get('results', []):
                results.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "snippet": item.get("description")
                })

            return {
                "query": query,
                "results": results,
                "count": len(results),
                "provider": "brave"
            }
        except Exception as e:
            return {"error": f"Brave error: {str(e)}"}


if __name__ == '__main__':
    WebSearchTool.main()

