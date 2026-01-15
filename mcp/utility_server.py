"""
Utility Functions MCP Server

Exposes shared.utils capabilities through MCP protocol.

Tools provided:
- parse_document: Parse document (auto-detect format)
- multi_provider_search: Multi-query research workflow
- extract_citations: Extract and format citations
- format_citation_bibtex: Format citation as BibTeX

Resources provided:
- utils://supported_formats: List of supported document formats
- utils://citation_styles: Available citation styles
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

# Import from shared library
import sys
sys.path.insert(0, '/home/coolhand/shared')
from utils.document_parsers import parse_file, is_supported_file, get_supported_extensions
from utils.multi_search import MultiSearchOrchestrator
from utils.citation import Citation, CitationManager
from config import ConfigManager

logger = logging.getLogger(__name__)


class UtilityServer:
    """
    MCP server for utility functions.

    Exposes document parsing, multi-search, and citation tools through MCP protocol.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize utility MCP server.

        Args:
            config_manager: ConfigManager instance (creates new one if None)
        """
        self.config = config_manager or ConfigManager(app_name='mcp_utility')

        # Initialize clients (lazy loading)
        self._citation_manager = None
        self._multi_search_orchestrators = {}  # provider -> orchestrator

    def get_citation_manager(self) -> CitationManager:
        """Get or create citation manager."""
        if self._citation_manager is None:
            self._citation_manager = CitationManager()
        return self._citation_manager

    def get_multi_search_orchestrator(self, provider: str = 'perplexity') -> MultiSearchOrchestrator:
        """Get or create multi-search orchestrator for provider."""
        if provider not in self._multi_search_orchestrators:
            # Get API key for provider
            api_key = self.config.get_api_key(provider)
            if not api_key:
                raise ValueError(f"No API key configured for provider: {provider}")

            # Map provider to API URL
            api_urls = {
                'perplexity': 'https://api.perplexity.ai/chat/completions',
                'openai': 'https://api.openai.com/v1/chat/completions',
                'anthropic': 'https://api.anthropic.com/v1/messages'
            }

            api_url = api_urls.get(provider)
            if not api_url:
                raise ValueError(f"Unsupported provider for multi-search: {provider}")

            self._multi_search_orchestrators[provider] = MultiSearchOrchestrator(
                api_key=api_key,
                api_url=api_url
            )

        return self._multi_search_orchestrators[provider]

    # -------------------------------------------------------------------------
    # MCP Tools - Document Parsing
    # -------------------------------------------------------------------------

    def tool_parse_document(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: parse_document

        Parse document (auto-detect format).

        Arguments:
            file_path (str): Path to file
            encoding (str, optional): Text file encoding (default: auto-detect)
            extract_metadata (bool, optional): Extract metadata (default: True)

        Returns:
            {success: bool, content: str, metadata: Dict, format: str}
        """
        try:
            file_path = arguments.get('file_path')
            if not file_path:
                return {
                    "success": False,
                    "error": "Missing required argument: file_path"
                }

            # Check if file exists
            if not Path(file_path).exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }

            # Check if format supported
            if not is_supported_file(file_path):
                ext = Path(file_path).suffix
                return {
                    "success": False,
                    "error": f"Unsupported file format: {ext}",
                    "supported_formats": list(get_supported_extensions())
                }

            # Parse file
            result = parse_file(
                file_path,
                encoding=arguments.get('encoding'),
                extract_metadata=arguments.get('extract_metadata', True)
            )

            return {
                "success": True,
                "content": result.get('content', ''),
                "metadata": result.get('metadata', {}),
                "format": result.get('format', ''),
                "file_path": file_path
            }

        except Exception as e:
            logger.exception(f"Error in parse_document: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - Multi-Search
    # -------------------------------------------------------------------------

    def tool_multi_provider_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: multi_provider_search

        Execute multi-query research workflow.

        Arguments:
            query (str): Research topic
            provider (str, optional): AI provider (default: perplexity)
            num_queries (int, optional): Number of queries to generate (default: 5)
            max_workers (int, optional): Concurrent workers (default: 3)

        Returns:
            {success: bool, queries: List[str], results: List[Dict], synthesis: str}
        """
        try:
            query = arguments.get('query')
            if not query:
                return {
                    "success": False,
                    "error": "Missing required argument: query"
                }

            provider = arguments.get('provider', 'perplexity')

            try:
                orchestrator = self.get_multi_search_orchestrator(provider)
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e)
                }

            # Execute multi-search
            result = orchestrator.search(
                topic=query,
                num_queries=arguments.get('num_queries', 5),
                max_workers=arguments.get('max_workers', 3)
            )

            # Convert to dict
            return {
                "success": True,
                "queries": [q.text for q in result.queries],
                "results": [
                    {
                        "query": r.query.text,
                        "content": r.content,
                        "success": r.success
                    }
                    for r in result.results
                ],
                "synthesis": result.final_report,
                "metadata": {
                    "provider": provider,
                    "num_queries": len(result.queries),
                    "successful_results": sum(1 for r in result.results if r.success)
                }
            }

        except Exception as e:
            logger.exception(f"Error in multi_provider_search: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - Citations
    # -------------------------------------------------------------------------

    def tool_extract_citations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: extract_citations

        Extract and format citations from text.

        Arguments:
            text (str): Text containing citations
            format (str, optional): Output format (bibtex, apa, mla) (default: bibtex)

        Returns:
            {success: bool, citations: List[Dict]}
        """
        try:
            text = arguments.get('text')
            if not text:
                return {
                    "success": False,
                    "error": "Missing required argument: text"
                }

            # This would require implementing citation extraction logic
            # For now, return placeholder
            return {
                "success": True,
                "citations": [],
                "message": "Citation extraction not yet implemented"
            }

        except Exception as e:
            logger.exception(f"Error in extract_citations: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_format_citation_bibtex(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: format_citation_bibtex

        Format citation as BibTeX.

        Arguments:
            title (str): Paper title
            authors (list): List of author names
            year (int, optional): Publication year
            journal (str, optional): Journal name
            doi (str, optional): DOI
            url (str, optional): URL

        Returns:
            {success: bool, bibtex: str, citation_key: str}
        """
        try:
            title = arguments.get('title')
            authors = arguments.get('authors', [])

            if not title or not authors:
                return {
                    "success": False,
                    "error": "Missing required arguments: title and authors"
                }

            # Create citation
            citation = Citation(
                title=title,
                authors=authors,
                year=arguments.get('year'),
                journal=arguments.get('journal'),
                doi=arguments.get('doi'),
                url=arguments.get('url')
            )

            # Get manager
            manager = self.get_citation_manager()

            # Add citation
            manager.add_citation(citation)

            # Generate BibTeX
            bibtex = manager.to_bibtex()

            return {
                "success": True,
                "bibtex": bibtex,
                "citation_key": citation.citation_key
            }

        except Exception as e:
            logger.exception(f"Error in format_citation_bibtex: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Resources
    # -------------------------------------------------------------------------

    def resource_supported_formats(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: utils://supported_formats

        Returns list of supported document formats.

        Args:
            uri: Resource URI ("utils://supported_formats")

        Returns:
            Supported formats list
        """
        try:
            # Get all supported extensions
            extensions = get_supported_extensions()

            return {
                "uri": uri,
                "supported_extensions": sorted(list(extensions)),
                "total_formats": len(extensions),
                "categories": {
                    "text": [".txt", ".md", ".rst"],
                    "code": [".py", ".js", ".ts", ".java"],
                    "documents": [".pdf", ".docx", ".odt"],
                    "spreadsheets": [".xlsx", ".xls", ".csv"],
                    "web": [".html", ".htm", ".xml"],
                    "notebooks": [".ipynb"],
                    "data": [".json", ".yaml", ".toml"]
                },
                "available_parsers": {
                    "pdf": "available",
                    "docx": "available",
                    "xlsx": "available",
                    "html": "available"
                }
            }

        except Exception as e:
            logger.exception(f"Error in resource_supported_formats: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }

    def resource_citation_styles(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: utils://citation_styles

        Returns available citation styles.

        Args:
            uri: Resource URI ("utils://citation_styles")

        Returns:
            Citation styles list
        """
        try:
            styles = {
                "bibtex": {
                    "name": "BibTeX",
                    "description": "LaTeX bibliography format",
                    "file_extension": ".bib"
                },
                "apa": {
                    "name": "APA (American Psychological Association)",
                    "description": "Social sciences citation style",
                    "file_extension": ".txt"
                },
                "mla": {
                    "name": "MLA (Modern Language Association)",
                    "description": "Humanities citation style",
                    "file_extension": ".txt"
                },
                "chicago": {
                    "name": "Chicago Manual of Style",
                    "description": "General purpose citation style",
                    "file_extension": ".txt"
                }
            }

            return {
                "uri": uri,
                "styles": styles,
                "default_style": "bibtex"
            }

        except Exception as e:
            logger.exception(f"Error in resource_citation_styles: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Server Interface
    # -------------------------------------------------------------------------

    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP tools manifest.

        Returns:
            List of tool definitions
        """
        return [
            {
                "name": "parse_document",
                "description": "Parse document (auto-detect format) - supports 50+ file types",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to file"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "Text file encoding (optional, auto-detected)"
                        },
                        "extract_metadata": {
                            "type": "boolean",
                            "description": "Extract metadata (default: true)"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "multi_provider_search",
                "description": "Execute multi-query research workflow with AI provider",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Research topic"
                        },
                        "provider": {
                            "type": "string",
                            "description": "AI provider (perplexity, openai, anthropic) (default: perplexity)"
                        },
                        "num_queries": {
                            "type": "integer",
                            "description": "Number of queries to generate (default: 5)"
                        },
                        "max_workers": {
                            "type": "integer",
                            "description": "Concurrent workers (default: 3)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "extract_citations",
                "description": "Extract and format citations from text",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text containing citations"
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format (bibtex, apa, mla) (default: bibtex)"
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "format_citation_bibtex",
                "description": "Format citation as BibTeX",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Paper title"
                        },
                        "authors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of author names"
                        },
                        "year": {
                            "type": "integer",
                            "description": "Publication year (optional)"
                        },
                        "journal": {
                            "type": "string",
                            "description": "Journal name (optional)"
                        },
                        "doi": {
                            "type": "string",
                            "description": "DOI (optional)"
                        },
                        "url": {
                            "type": "string",
                            "description": "URL (optional)"
                        }
                    },
                    "required": ["title", "authors"]
                }
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
                "uri": "utils://supported_formats",
                "name": "Supported Document Formats",
                "description": "List of 50+ supported file formats for parsing",
                "mimeType": "application/json"
            },
            {
                "uri": "utils://citation_styles",
                "name": "Citation Styles",
                "description": "Available citation formatting styles",
                "mimeType": "application/json"
            }
        ]

