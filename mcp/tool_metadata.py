"""
Rich Tool Metadata for MCP Server

Provides comprehensive metadata for all MCP tools including:
- Descriptions and examples
- Cost estimates
- Execution time estimates
- Use cases and workflows
- Input/output schemas

Author: Luke Steuber
Date: 2025-11-20
"""

from typing import Dict, List, Any

# Tool metadata organized by category
TOOL_METADATA = {
    # ===== LLM Provider Tools =====
    "create_provider": {
        "category": "llm",
        "description": "Create and cache an LLM provider instance for subsequent calls",
        "cost_estimate": {"min": 0, "max": 0, "avg": 0},
        "execution_time": "< 1s",
        "use_cases": [
            "Initialize provider before multiple chat calls",
            "Test provider availability",
            "Check provider capabilities"
        ],
        "examples": [
            {
                "input": {"provider_name": "anthropic", "model": "claude-sonnet-4-5"},
                "output": {"success": True, "provider": "anthropic", "supports_vision": True}
            }
        ],
        "tips": [
            "Provider instances are cached for reuse",
            "Check API key is set before creating provider",
            "Use list_provider_models to see available models"
        ]
    },
    
    "chat_completion": {
        "category": "llm",
        "description": "Generate chat completion using any LLM provider",
        "cost_estimate": {"min": 0.001, "max": 0.20, "avg": 0.02},
        "execution_time": "1-5s (depends on provider and model)",
        "use_cases": [
            "General Q&A and conversations",
            "Code generation and review",
            "Text analysis and summarization",
            "Content generation"
        ],
        "examples": [
            {
                "input": {
                    "provider_name": "anthropic",
                    "messages": [{"role": "user", "content": "What is Python?"}],
                    "max_tokens": 100
                },
                "output": {"success": True, "content": "Python is..."}
            }
        ],
        "tips": [
            "Use max_tokens to control cost",
            "Simple queries → use mini/haiku models for savings",
            "Cache results for identical queries"
        ]
    },
    
    "generate_image": {
        "category": "llm",
        "description": "Generate image using DALL-E (OpenAI) or Aurora (xAI)",
        "cost_estimate": {"min": 0.02, "max": 0.08, "avg": 0.04},
        "execution_time": "5-15s",
        "use_cases": [
            "Visualizations for reports",
            "Concept art and mockups",
            "Educational diagrams",
            "Marketing materials"
        ],
        "examples": [
            {
                "input": {
                    "provider_name": "openai",
                    "prompt": "A serene mountain landscape at sunset"
                },
                "output": {"success": True, "image_data": "base64...", "model": "dall-e-3"}
            }
        ],
        "tips": [
            "Be specific in prompts for better results",
            "DALL-E-3 provides revised prompts showing interpretation",
            "xAI Aurora is faster but may have different style"
        ]
    },
    
    "analyze_image": {
        "category": "llm",
        "description": "Analyze image using vision-capable LLM",
        "cost_estimate": {"min": 0.01, "max": 0.15, "avg": 0.05},
        "execution_time": "2-8s",
        "use_cases": [
            "Generate alt text for accessibility",
            "Extract text from images (OCR)",
            "Identify objects and scenes",
            "Analyze charts and diagrams"
        ],
        "examples": [
            {
                "input": {
                    "provider_name": "anthropic",
                    "image_data": "base64_encoded_image",
                    "prompt": "Describe this image"
                },
                "output": {"success": True, "content": "The image shows..."}
            }
        ],
        "tips": [
            "Claude (Anthropic) excels at detailed analysis",
            "GPT-4V (OpenAI) good for OCR",
            "Grok (xAI) fastest for simple descriptions"
        ]
    },
    
    # ===== Data Fetching Tools =====
    "dream_of_arxiv": {
        "category": "data",
        "description": "Search arXiv for academic papers",
        "cost_estimate": {"min": 0, "max": 0, "avg": 0},
        "execution_time": "500ms-2s",
        "use_cases": [
            "Literature reviews",
            "Finding relevant research",
            "Checking publication history",
            "Building bibliography"
        ],
        "examples": [
            {
                "input": {
                    "query": "transformer architectures",
                    "max_results": 10,
                    "sort_by": "relevance"
                },
                "output": {"success": True, "papers": [...], "metadata": {...}}
            }
        ],
        "tips": [
            "Use category filters for targeted search (cat:cs.CL)",
            "Cache results for expensive searches",
            "Combine with parse_document to extract PDF content"
        ]
    },
    
    "dream_of_census_acs": {
        "category": "data",
        "description": "Fetch American Community Survey demographics from Census Bureau",
        "cost_estimate": {"min": 0, "max": 0, "avg": 0},
        "execution_time": "1-3s (or from cache)",
        "use_cases": [
            "Demographic analysis",
            "Poverty research",
            "Income distribution studies",
            "Geographic comparisons"
        ],
        "examples": [
            {
                "input": {
                    "year": 2022,
                    "variables": {"B19013_001E": "median_income"},
                    "geography": "county:*",
                    "state": "06"
                },
                "output": {"success": True, "records": [...], "metadata": {...}}
            }
        ],
        "tips": [
            "Results are automatically cached",
            "Use state filter to limit results",
            "Find variable codes at data.census.gov"
        ]
    },
    
    # ===== Caching Tools =====
    "cache_set": {
        "category": "cache",
        "description": "Store value in Redis cache with optional TTL",
        "cost_estimate": {"min": 0, "max": 0, "avg": 0},
        "execution_time": "<5ms",
        "use_cases": [
            "Cache expensive API results",
            "Store session data",
            "Share data between tools",
            "Rate limiting counters"
        ],
        "examples": [
            {
                "input": {
                    "key": "research_results",
                    "value": {"findings": "..."},
                    "ttl": 3600
                },
                "output": {"success": True, "key": "research_results", "ttl": 3600}
            }
        ],
        "tips": [
            "Use namespaces for organization",
            "Set appropriate TTL for data freshness",
            "Check cache_exists before expensive operations"
        ]
    },
    
    "cache_get": {
        "category": "cache",
        "description": "Retrieve cached value from Redis",
        "cost_estimate": {"min": 0, "max": 0, "avg": 0},
        "execution_time": "<5ms",
        "use_cases": [
            "Retrieve cached results",
            "Avoid redundant API calls",
            "Fast data access",
            "Session recovery"
        ],
        "examples": [
            {
                "input": {"key": "research_results"},
                "output": {"success": True, "value": {...}, "found": True}
            }
        ],
        "tips": [
            "Returns null if key not found",
            "Use cache_exists to check before getting",
            "Consider cache_list_keys to discover available data"
        ]
    },
    
    # ===== Utility Tools =====
    "parse_document": {
        "category": "utility",
        "description": "Parse document (auto-detects format) - supports 50+ file types",
        "cost_estimate": {"min": 0, "max": 0, "avg": 0},
        "execution_time": "100ms-5s (depends on file size)",
        "use_cases": [
            "Extract text from PDFs",
            "Parse Excel/CSV data",
            "Read code files",
            "Process notebooks (Jupyter)",
            "Parse HTML/XML"
        ],
        "examples": [
            {
                "input": {"file_path": "/path/to/document.pdf"},
                "output": {
                    "success": True,
                    "content": "Full document text...",
                    "metadata": {"pages": 10, "author": "..."}
                }
            }
        ],
        "tips": [
            "Supports PDF, DOCX, XLSX, CSV, HTML, code, notebooks",
            "Automatically detects format from extension",
            "Cache parsed content for reuse",
            "Use with chat_completion for document analysis"
        ]
    },
    
    # ===== Orchestration Tools =====
    "dream_research": {
        "category": "orchestration",
        "description": "Hierarchical research using Dream Cascade (3-tier synthesis)",
        "cost_estimate": {"min": 0.50, "max": 3.00, "avg": 1.25},
        "execution_time": "3-10 minutes (depends on agents)",
        "use_cases": [
            "Comprehensive research reports",
            "Literature reviews",
            "Multi-source synthesis",
            "In-depth topic analysis"
        ],
        "examples": [
            {
                "input": {
                    "task": "Evolution of transformer architectures 2017-2025",
                    "num_agents": 9,
                    "enable_synthesis": True
                },
                "output": {
                    "success": True,
                    "task_id": "belta-...",
                    "final_report": "15-page comprehensive analysis...",
                    "documents": ["report.pdf", "report.docx"]
                }
            }
        ],
        "tips": [
            "Start with 5-7 agents, scale up as needed",
            "Enable synthesis for hierarchical processing",
            "Monitor progress with dreamwalker_status",
            "Generate documents in PDF/DOCX for deliverables"
        ]
    },
    
    "dream_search": {
        "category": "orchestration",
        "description": "Multi-agent search using Dream Swarm (specialized agents)",
        "cost_estimate": {"min": 0.20, "max": 1.50, "avg": 0.60},
        "execution_time": "1-5 minutes (depends on agents)",
        "use_cases": [
            "Fact checking across sources",
            "Trend analysis",
            "Multi-platform research",
            "Verification workflows"
        ],
        "examples": [
            {
                "input": {
                    "query": "quantum computing breakthroughs 2024",
                    "num_agents": 6,
                    "agent_types": ["academic", "news", "technical"]
                },
                "output": {
                    "success": True,
                    "task_id": "swarm-...",
                    "results": [...]
                }
            }
        ],
        "tips": [
            "Specify agent_types for focused search",
            "Use parallel_execution for speed",
            "Combine with dream_research for deep dives",
            "Faster and cheaper than dream_research"
        ]
    }
}


def get_tool_metadata(tool_name: str) -> Dict[str, Any]:
    """
    Get metadata for a specific tool.
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        Tool metadata dictionary or empty dict if not found
    """
    return TOOL_METADATA.get(tool_name, {})


def get_tools_by_category(category: str) -> List[str]:
    """
    Get list of tools in a category.
    
    Args:
        category: Category name (llm, data, cache, utility, orchestration)
    
    Returns:
        List of tool names
    """
    return [
        name for name, meta in TOOL_METADATA.items()
        if meta.get('category') == category
    ]


def get_cost_estimate(tool_name: str) -> Dict[str, float]:
    """
    Get cost estimate for a tool.
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        Cost estimate dictionary with min, max, avg
    """
    meta = TOOL_METADATA.get(tool_name, {})
    return meta.get('cost_estimate', {"min": 0, "max": 0, "avg": 0, "unknown": True})


def enrich_tool_manifest(tool_manifest: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich tool manifest with additional metadata.
    
    Args:
        tool_manifest: Original tool manifest from sub-servers
    
    Returns:
        Enriched manifest with metadata, examples, cost estimates
    """
    enriched = []
    
    for tool in tool_manifest:
        tool_name = tool.get('name')
        metadata = get_tool_metadata(tool_name)
        
        # Merge metadata into tool definition
        enriched_tool = {
            **tool,
            **metadata
        }
        
        enriched.append(enriched_tool)
    
    return enriched


__all__ = [
    'TOOL_METADATA',
    'get_tool_metadata',
    'get_tools_by_category',
    'get_cost_estimate',
    'enrich_tool_manifest'
]
