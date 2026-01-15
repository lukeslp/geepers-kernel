"""
Data tool registry helper - one-line registration for all data fetching tools.

This module provides a convenience function to register all 12 data fetching tool
modules with the ToolRegistry in one call, eliminating boilerplate code.

Usage:
    from shared.tools import register_data_tools, get_registry

    # Register all data tools
    result = register_data_tools()
    print(f"Registered: {result['registered']}")

    # Use registered tools
    registry = get_registry()
    papers = registry.execute_tool('arxiv_search', {'query': 'quantum computing'})
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def register_data_tools(skip_errors: bool = True) -> Dict[str, Any]:
    """
    Register all data fetching tool modules with the ToolRegistry.

    This function attempts to import and register all 12 data tool modules:
    - archive_tool (Internet Archive)
    - arxiv_tool (arXiv papers)
    - census_tool (Census Bureau)
    - finance_tool (Financial data)
    - github_tool (GitHub)
    - nasa_tool (NASA APIs)
    - news_tool (News API)
    - openlibrary_tool (OpenLibrary)
    - semantic_scholar_tool (Semantic Scholar)
    - weather_tool (Weather data)
    - wikipedia_tool (Wikipedia)
    - youtube_tool (YouTube)

    Args:
        skip_errors: If True, continue registration even if some tools fail to load.
                    If False, raise exception on first error.

    Returns:
        Dict with:
            'registered': List of successfully registered tool names
            'errors': Dict mapping tool names to error messages
            'total': Total number of tools attempted

    Example:
        >>> from shared.tools import register_data_tools
        >>> result = register_data_tools()
        >>> print(f"Registered {len(result['registered'])} tools")
        Registered 12 tools
        >>> print(result['registered'])
        ['archive', 'arxiv', 'census', 'finance', 'github', 'nasa', ...]
    """
    from .registry import ToolRegistry

    # Tool module names and their import paths
    TOOL_MODULES = [
        ("archive", "archive_tool", "ArchiveTools"),
        ("arxiv", "arxiv_tool", "ArxivTools"),
        ("census", "census_tool", "CensusTools"),
        ("finance", "finance_tool", "FinanceTools"),
        ("github", "github_tool", "GitHubTools"),
        ("nasa", "nasa_tool", "NASATools"),
        ("news", "news_tool", "NewsTools"),
        ("openlibrary", "openlibrary_tool", "OpenLibraryTools"),
        ("semantic_scholar", "semantic_scholar_tool", "SemanticScholarTools"),
        ("weather", "weather_tool", "WeatherTools"),
        ("wikipedia", "wikipedia_tool", "WikipediaTools"),
        ("youtube", "youtube_tool", "YouTubeTools"),
    ]

    ToolRegistry.get_instance()
    registered = []
    errors = {}

    for tool_name, module_name, class_name in TOOL_MODULES:
        try:
            # Dynamic import of tool module
            module = __import__(f"tools.{module_name}", fromlist=[class_name])
            tool_class = getattr(module, class_name)

            # Instantiate and register
            tool_instance = tool_class()
            tool_instance.register_with_registry()

            registered.append(tool_name)
            logger.info(f"Registered data tool: {tool_name}")

        except ImportError as e:
            error_msg = f"Import error: {str(e)}"
            errors[tool_name] = error_msg
            logger.warning(f"Failed to import {tool_name}: {error_msg}")
            if not skip_errors:
                raise

        except AttributeError as e:
            error_msg = f"Class {class_name} not found in module: {str(e)}"
            errors[tool_name] = error_msg
            logger.warning(f"Failed to load {tool_name}: {error_msg}")
            if not skip_errors:
                raise

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            errors[tool_name] = error_msg
            logger.error(f"Failed to register {tool_name}: {error_msg}")
            if not skip_errors:
                raise

    return {"registered": registered, "errors": errors, "total": len(TOOL_MODULES)}


def get_data_tool_status() -> Dict[str, Any]:
    """
    Check registration status of all data tools.

    Returns:
        Dict with:
            'registered_tools': List of registered data tool names
            'missing_tools': List of expected but not registered tools
            'total_registered': Count of registered tools
            'total_expected': Count of expected tools (12)

    Example:
        >>> from shared.tools import get_data_tool_status
        >>> status = get_data_tool_status()
        >>> print(f"{status['total_registered']}/{status['total_expected']} tools registered")
        12/12 tools registered
    """
    from .registry import ToolRegistry

    EXPECTED_TOOLS = [
        "archive",
        "arxiv",
        "census",
        "finance",
        "github",
        "nasa",
        "news",
        "openlibrary",
        "semantic_scholar",
        "weather",
        "wikipedia",
        "youtube",
    ]

    registry = ToolRegistry.get_instance()
    all_tools = list(registry.get_all_tools().keys())

    # Filter to only data tools (may have namespaces like 'data.arxiv')
    registered = [tool for tool in EXPECTED_TOOLS if any(tool in t for t in all_tools)]

    missing = [tool for tool in EXPECTED_TOOLS if tool not in registered]

    return {
        "registered_tools": registered,
        "missing_tools": missing,
        "total_registered": len(registered),
        "total_expected": len(EXPECTED_TOOLS),
    }
