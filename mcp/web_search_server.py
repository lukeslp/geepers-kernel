"""
Web Search MCP Server

Exposes web search capabilities through MCP protocol via multiple providers:
- SerpAPI (Google Search)
- Tavily Search
- Brave Search

Tools provided:
- web_search: Search the web using available providers (auto-selects or manual)

Resources provided:
- websearch://providers: List configured search providers

Author: Luke Steuber
"""

import json
import logging
import sys
from typing import Any, Dict, List, Optional

# Import from shared library
sys.path.insert(0, "/home/coolhand/shared")

from config import ConfigManager
from tools.web_search_tool import WebSearchTool

logger = logging.getLogger(__name__)


class WebSearchServer:
    """
    MCP server for web search capabilities.

    Exposes web search across SerpAPI, Tavily, and Brave through MCP protocol.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize web search MCP server.

        Args:
            config_manager: ConfigManager instance (creates new one if None)
        """
        self.config = config_manager or ConfigManager(app_name="mcp_web_search")

        # Initialize web search tool (lazy loading)
        self._web_search_tool = None

    def get_web_search_tool(self) -> WebSearchTool:
        """Get or create WebSearchTool instance."""
        if self._web_search_tool is None:
            self._web_search_tool = WebSearchTool()
            self._web_search_tool.initialize()
        return self._web_search_tool

    # -------------------------------------------------------------------------
    # MCP Tools - Web Search
    # -------------------------------------------------------------------------

    def tool_web_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: web_search

        Search the web using available search providers (SerpAPI, Tavily, Brave).
        Auto-selects first available provider unless specified.

        Arguments:
            query (str): Search query string
            provider (str, optional): Provider to use: 'serpapi', 'tavily', 'brave', or 'auto' (default: 'auto')
            num_results (int, optional): Number of results to return (default: 10)

        Returns:
            {success: bool, query: str, results: List[Dict], provider: str, count: int}
            or {success: False, error: str}
        """
        try:
            # Extract and validate arguments
            query = arguments.get("query")
            if not query:
                return {"success": False, "error": "Missing required argument: query"}

            provider = arguments.get("provider", "auto")
            num_results = arguments.get("num_results", 10)

            # Validate provider
            valid_providers = ["serpapi", "tavily", "brave", "auto"]
            if provider not in valid_providers:
                return {
                    "success": False,
                    "error": f"Invalid provider '{provider}'. Must be one of: {', '.join(valid_providers)}",
                }

            # Validate num_results
            if not isinstance(num_results, int) or num_results < 1:
                return {"success": False, "error": "num_results must be a positive integer"}

            # Execute search
            tool = self.get_web_search_tool()
            result = tool.web_search(query=query, provider=provider, num_results=num_results)

            # Check if tool returned an error
            if "error" in result:
                return {"success": False, "error": result["error"]}

            # Return successful result
            return {
                "success": True,
                "query": result.get("query", query),
                "results": result.get("results", []),
                "provider": result.get("provider", provider),
                "count": result.get("count", len(result.get("results", []))),
            }

        except Exception as e:
            logger.exception(f"Error in web_search: {e}")
            return {"success": False, "error": f"Web search error: {str(e)}"}

    # -------------------------------------------------------------------------
    # MCP Resources
    # -------------------------------------------------------------------------

    def resource_providers(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: websearch://providers

        Returns information about configured search providers.

        Args:
            uri: Resource URI (e.g., "websearch://providers")

        Returns:
            Provider availability information
        """
        try:
            tool = self.get_web_search_tool()

            providers = {
                "serpapi": {
                    "name": "SerpAPI (Google Search)",
                    "configured": bool(tool.serp_key),
                    "url": "https://serpapi.com",
                },
                "tavily": {
                    "name": "Tavily Search",
                    "configured": bool(tool.tavily_key),
                    "url": "https://tavily.com",
                },
                "brave": {
                    "name": "Brave Search",
                    "configured": bool(tool.brave_key),
                    "url": "https://brave.com/search/api/",
                },
            }

            available_providers = [name for name, info in providers.items() if info["configured"]]

            return {
                "uri": uri,
                "providers": providers,
                "available": available_providers,
                "default": available_providers[0] if available_providers else None,
                "message": f"{len(available_providers)} provider(s) configured"
                if available_providers
                else "No providers configured - set SERP_API_KEY, TAVILY_API_KEY, or BRAVE_API_KEY",
            }

        except Exception as e:
            logger.exception(f"Error in resource_providers: {e}")
            return {"uri": uri, "error": str(e)}

    # -------------------------------------------------------------------------
    # MCP Manifests
    # -------------------------------------------------------------------------

    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP tools manifest.

        Returns:
            List of tool definitions in MCP format
        """
        return [
            {
                "name": "web_search",
                "description": "Search the web using SerpAPI, Tavily, or Brave. Auto-selects first available provider or use specific provider.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"},
                        "provider": {
                            "type": "string",
                            "enum": ["serpapi", "tavily", "brave", "auto"],
                            "description": "Search provider to use (default: auto - selects first available)",
                            "default": "auto",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of search results to return (default: 10)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100,
                        },
                    },
                    "required": ["query"],
                },
            }
        ]

    def get_resources_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP resources manifest.

        Returns:
            List of resource templates
        """
        return [
            {
                "uri": "websearch://providers",
                "name": "Web Search Providers",
                "description": "Information about configured search providers (SerpAPI, Tavily, Brave)",
                "mimeType": "application/json",
            }
        ]


# For testing/standalone usage
if __name__ == "__main__":
    pass

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Create server
    server = WebSearchServer()

    # Test provider availability
    print("Testing Web Search MCP Server")
    print("=" * 60)

    providers_info = server.resource_providers("websearch://providers")
    print(f"\nProvider Status:")
    print(json.dumps(providers_info, indent=2))

    # Test search if any provider is configured
    if providers_info.get("available"):
        print(f"\n\nTesting search with query 'Claude Code MCP'...")
        result = server.tool_web_search(
            {"query": "Claude Code MCP", "provider": "auto", "num_results": 3}
        )

        if result.get("success"):
            print(f"\nProvider: {result['provider']}")
            print(f"Results: {result['count']}")
            for i, item in enumerate(result.get("results", [])[:3], 1):
                print(f"\n{i}. {item.get('title')}")
                print(f"   {item.get('url')}")
                print(f"   {item.get('snippet', '')[:100]}...")
        else:
            print(f"\nError: {result.get('error')}")
    else:
        print("\n\nNo providers configured. Set one of:")
        print("  - SERP_API_KEY or SERPAPI_API_KEY")
        print("  - TAVILY_API_KEY")
        print("  - BRAVE_API_KEY")
