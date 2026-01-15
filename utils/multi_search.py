"""
Multi-search orchestration utilities for comprehensive research.

This module provides a generalized pattern for multi-query research workflows:
1. Query Generation - Expand a topic into multiple targeted queries
2. Parallel Execution - Execute searches concurrently for efficiency
3. Result Synthesis - Combine results into comprehensive report

The orchestrator is provider-agnostic and works with any AI/search API that
follows the chat completion interface (OpenAI-compatible).

Features:
- Concurrent query execution with ThreadPoolExecutor
- Customizable query generation and synthesis prompts
- Flexible callback system for progress tracking
- Support for any AI provider (Perplexity, OpenAI, Anthropic, etc.)
- Structured result objects with metadata

Usage:
    from shared.utils.multi_search import MultiSearchOrchestrator

    # Initialize with API credentials
    orchestrator = MultiSearchOrchestrator(
        api_key="your-api-key",
        api_url="https://api.perplexity.ai/chat/completions"
    )

    # Execute multi-search
    result = orchestrator.search("quantum computing applications")
    print(result.final_report)

Author: Luke Steuber
"""

import os
import json
import logging
import requests
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SearchQuery:
    """
    Represents a single search query in multi-search workflow.

    Attributes:
        text: The query text
        index: Position in query list (1-based)
        total: Total number of queries in batch
        metadata: Additional query metadata
    """
    text: str
    index: int
    total: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """
    Result from a single search query execution.

    Attributes:
        query: The original query
        content: Response content from AI
        success: Whether search succeeded
        error: Error message if failed
        raw_response: Full API response
        metadata: Additional result metadata
    """
    query: SearchQuery
    content: str
    success: bool
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiSearchResult:
    """
    Final result from multi-search orchestration.

    Attributes:
        original_query: The initial search topic
        generated_queries: List of expanded queries
        search_results: Individual search results
        final_report: Synthesized comprehensive report
        success: Whether full workflow succeeded
        error: Error message if failed
        metadata: Workflow metadata (timings, counts, etc.)
    """
    original_query: str
    generated_queries: List[str]
    search_results: List[SearchResult]
    final_report: str
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Multi-Search Orchestrator
# ============================================================================

class MultiSearchOrchestrator:
    """
    Orchestrates multi-query research workflows with concurrent execution.

    This class implements the map-reduce pattern for comprehensive research:
    1. Generate N targeted queries from a broad topic (map)
    2. Execute all queries concurrently (map)
    3. Synthesize results into unified report (reduce)

    Example:
        >>> orchestrator = MultiSearchOrchestrator(
        ...     api_key=os.environ["PERPLEXITY_API_KEY"],
        ...     api_url="https://api.perplexity.ai/chat/completions"
        ... )
        >>> result = orchestrator.search("machine learning trends 2025")
        >>> print(result.final_report)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = "https://api.perplexity.ai/chat/completions",
        query_model: str = "sonar",
        search_model: str = "sonar",
        synthesis_model: str = "sonar-pro",
        num_queries: int = 5,
        max_workers: int = 5,
        timeout: int = 60
    ):
        """
        Initialize multi-search orchestrator.

        Args:
            api_key: API key for the provider (falls back to PERPLEXITY_API_KEY env var)
            api_url: Base URL for chat completions endpoint
            query_model: Model for query generation
            search_model: Model for individual searches
            synthesis_model: Model for final synthesis
            num_queries: Number of queries to generate (default: 5)
            max_workers: Max concurrent searches (default: 5)
            timeout: Request timeout in seconds (default: 60)

        Raises:
            ValueError: If API key not provided and not in environment
        """
        self.api_key = api_key or os.environ.get("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Provide via api_key parameter or set "
                "PERPLEXITY_API_KEY environment variable."
            )

        self.api_url = api_url
        self.query_model = query_model
        self.search_model = search_model
        self.synthesis_model = synthesis_model
        self.num_queries = num_queries
        self.max_workers = max_workers
        self.timeout = timeout

        logger.info(
            f"Initialized MultiSearchOrchestrator with {num_queries} queries, "
            f"{max_workers} workers"
        )

    def search(
        self,
        topic: str,
        on_queries_generated: Optional[Callable[[List[str]], None]] = None,
        on_search_complete: Optional[Callable[[SearchResult], None]] = None,
        on_synthesis_start: Optional[Callable[[], None]] = None
    ) -> MultiSearchResult:
        """
        Execute full multi-search workflow.

        Args:
            topic: The research topic to investigate
            on_queries_generated: Callback when queries are generated
            on_search_complete: Callback after each individual search
            on_synthesis_start: Callback before final synthesis

        Returns:
            MultiSearchResult with comprehensive report

        Example:
            >>> def log_queries(queries):
            ...     print(f"Generated {len(queries)} queries")
            >>>
            >>> result = orchestrator.search(
            ...     "renewable energy",
            ...     on_queries_generated=log_queries
            ... )
        """
        logger.info(f"Starting multi-search for: {topic}")

        try:
            # Stage 1: Generate multiple queries
            queries = self._generate_queries(topic)
            if on_queries_generated:
                on_queries_generated(queries)

            # Stage 2: Execute searches concurrently
            results = self._execute_searches(queries, on_search_complete)

            # Stage 3: Synthesize into comprehensive report
            if on_synthesis_start:
                on_synthesis_start()
            report = self._synthesize_report(topic, queries, results)

            logger.info("Multi-search completed successfully")

            return MultiSearchResult(
                original_query=topic,
                generated_queries=queries,
                search_results=results,
                final_report=report,
                success=True,
                metadata={
                    "num_queries": len(queries),
                    "num_successful": sum(1 for r in results if r.success),
                    "num_failed": sum(1 for r in results if not r.success)
                }
            )

        except Exception as e:
            logger.error(f"Multi-search failed: {e}")
            return MultiSearchResult(
                original_query=topic,
                generated_queries=[],
                search_results=[],
                final_report="",
                success=False,
                error=str(e)
            )

    def _generate_queries(self, topic: str) -> List[str]:
        """
        Generate multiple targeted queries from a broad topic.

        Args:
            topic: The research topic

        Returns:
            List of generated query strings
        """
        logger.info(f"Generating {self.num_queries} queries for: {topic}")

        prompt = (
            f"Based on the topic '{topic}', create exactly {self.num_queries} "
            f"specific search queries that would help gather comprehensive information. "
            f"Format your response as a JSON array of strings."
        )

        response = self._make_request(
            prompt,
            system_message=(
                "You are a helpful assistant specialized in creating targeted search "
                "queries. For any topic, create specific search queries that would help "
                "gather comprehensive information."
            ),
            model=self.query_model
        )

        # Extract queries from response
        queries = self._extract_queries_from_response(response)

        # Fallback to original topic if extraction failed
        if not queries:
            logger.warning("Could not generate queries, using original topic")
            queries = [topic]

        # Limit to requested number
        queries = queries[:self.num_queries]

        logger.info(f"Generated {len(queries)} queries")
        return queries

    def _execute_searches(
        self,
        queries: List[str],
        on_complete: Optional[Callable[[SearchResult], None]] = None
    ) -> List[SearchResult]:
        """
        Execute all queries concurrently using ThreadPoolExecutor.

        Args:
            queries: List of query strings
            on_complete: Callback after each search completes

        Returns:
            List of SearchResult objects
        """
        logger.info(f"Executing {len(queries)} searches with {self.max_workers} workers")

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all searches
            future_to_query = {
                executor.submit(self._execute_single_search, query, i + 1, len(queries)): query
                for i, query in enumerate(queries)
            }

            # Collect results as they complete
            for future in as_completed(future_to_query):
                result = future.result()
                results.append(result)

                if on_complete:
                    on_complete(result)

        # Sort by original index to maintain order
        results.sort(key=lambda r: r.query.index)

        logger.info(
            f"Completed {len(results)} searches "
            f"({sum(1 for r in results if r.success)} successful)"
        )
        return results

    def _execute_single_search(
        self,
        query: str,
        index: int,
        total: int
    ) -> SearchResult:
        """
        Execute a single search query.

        Args:
            query: Query text
            index: Query position (1-based)
            total: Total number of queries

        Returns:
            SearchResult object
        """
        logger.info(f"Executing search {index}/{total}: {query}")

        search_query = SearchQuery(text=query, index=index, total=total)

        try:
            response = self._make_request(
                f"Search for: {query}",
                system_message=(
                    "You are a helpful assistant that searches the web for information. "
                    "Be precise, thorough and concise."
                ),
                model=self.search_model
            )

            content = self._extract_content_from_response(response)

            return SearchResult(
                query=search_query,
                content=content,
                success=True,
                raw_response=response
            )

        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return SearchResult(
                query=search_query,
                content="",
                success=False,
                error=str(e)
            )

    def _synthesize_report(
        self,
        topic: str,
        queries: List[str],
        results: List[SearchResult]
    ) -> str:
        """
        Synthesize individual search results into comprehensive report.

        Args:
            topic: Original research topic
            queries: List of query strings
            results: List of SearchResult objects

        Returns:
            Synthesized report text
        """
        logger.info("Generating comprehensive report")

        # Compile all search results
        result_sections = []
        for result in results:
            if result.success:
                section = (
                    f"SEARCH RESULT #{result.query.index} "
                    f"(Query: {result.query.text}):\n{result.content}"
                )
                result_sections.append(section)

        combined = '\n\n'.join(result_sections)

        # Generate synthesis
        prompt = f"""
Create a comprehensive report about "{topic}" based on the following search results:

{combined}

Provide a well-structured report with key findings, details, and conclusions.
"""

        response = self._make_request(
            prompt,
            system_message=(
                "You are a helpful assistant specialized in creating comprehensive "
                "research reports. Synthesize information from multiple sources into "
                "a well-structured report."
            ),
            model=self.synthesis_model,
            max_tokens=10000
        )

        report = self._extract_content_from_response(response)
        logger.info("Report generation complete")
        return report

    def _make_request(
        self,
        user_message: str,
        system_message: str,
        model: str,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make API request to chat completion endpoint.

        Args:
            user_message: User message content
            system_message: System message content
            model: Model identifier
            max_tokens: Maximum tokens in response

        Returns:
            API response dictionary

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            self.api_url,
            json=payload,
            headers=headers,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def _extract_queries_from_response(self, response: Dict[str, Any]) -> List[str]:
        """
        Extract query list from API response.

        Args:
            response: API response dictionary

        Returns:
            List of extracted queries
        """
        queries = []

        if "choices" not in response or not response["choices"]:
            return queries

        content = response["choices"][0]["message"]["content"]

        # Try JSON parsing first
        try:
            if "[" in content and "]" in content:
                json_str = content[content.find("["):content.rfind("]") + 1]
                queries = json.loads(json_str)
                return queries
        except json.JSONDecodeError:
            pass

        # Fall back to line-by-line parsing
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()

            # Skip empty, headers, and markdown
            if not line or line.startswith(("#", "-", "*", "```")):
                continue

            # Extract numbered items (1. Query text)
            if line[0].isdigit() and "." in line:
                query_text = line.split(".", 1)[1].strip()
                if query_text:
                    queries.append(query_text)
            # Add non-numbered lines that look like queries
            elif len(line) > 10:
                queries.append(line)

        return queries

    def _extract_content_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract content text from API response.

        Args:
            response: API response dictionary

        Returns:
            Extracted content string
        """
        if "choices" in response and response["choices"]:
            return response["choices"][0]["message"]["content"]
        return ""


# ============================================================================
# Functional Interface (Convenience Functions)
# ============================================================================

def multi_search(
    topic: str,
    api_key: Optional[str] = None,
    api_url: str = "https://api.perplexity.ai/chat/completions",
    num_queries: int = 5,
    max_workers: int = 5,
    verbose: bool = False
) -> MultiSearchResult:
    """
    Execute multi-search workflow (functional interface).

    Args:
        topic: Research topic
        api_key: API key (falls back to PERPLEXITY_API_KEY env var)
        api_url: API endpoint URL
        num_queries: Number of queries to generate
        max_workers: Max concurrent searches
        verbose: Print progress messages

    Returns:
        MultiSearchResult with comprehensive report

    Example:
        >>> from shared.utils import multi_search
        >>> result = multi_search("AI safety research", num_queries=3)
        >>> print(result.final_report)
    """
    orchestrator = MultiSearchOrchestrator(
        api_key=api_key,
        api_url=api_url,
        num_queries=num_queries,
        max_workers=max_workers
    )

    # Add verbose callbacks if requested
    callbacks = {}
    if verbose:
        callbacks["on_queries_generated"] = lambda q: print(f"Generated {len(q)} queries")
        callbacks["on_search_complete"] = lambda r: print(
            f"✓ Search {r.query.index}/{r.query.total} complete"
        )
        callbacks["on_synthesis_start"] = lambda: print("Synthesizing report...")

    return orchestrator.search(topic, **callbacks)


# ============================================================================
# Testing
# ============================================================================

def _test_multi_search():
    """Test function for standalone testing."""
    print("Testing MultiSearchOrchestrator...")

    # Check for API key
    if not os.environ.get("PERPLEXITY_API_KEY"):
        print("\nERROR: PERPLEXITY_API_KEY environment variable required")
        print("Set with: export PERPLEXITY_API_KEY=your-key-here")
        return

    print("\n1. Testing query generation...")
    orchestrator = MultiSearchOrchestrator(num_queries=3, max_workers=2)

    # Test query generation only
    queries = orchestrator._generate_queries("Python async programming")
    print(f"   Generated {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q}")

    print("\n2. Testing full multi-search workflow...")

    def on_queries(q):
        print(f"   → Generated {len(q)} queries")

    def on_search(r):
        status = "✓" if r.success else "✗"
        print(f"   {status} Search {r.query.index}/{r.query.total}: {r.query.text[:50]}...")

    def on_synthesis():
        print("   → Synthesizing final report...")

    result = orchestrator.search(
        "machine learning interpretability",
        on_queries_generated=on_queries,
        on_search_complete=on_search,
        on_synthesis_start=on_synthesis
    )

    if result.success:
        print(f"\n✅ Multi-search successful!")
        print(f"   Queries: {len(result.generated_queries)}")
        print(f"   Successful searches: {result.metadata['num_successful']}")
        print(f"   Report length: {len(result.final_report)} chars")
        print(f"\nFirst 200 chars of report:")
        print(f"   {result.final_report[:200]}...")
    else:
        print(f"\n❌ Multi-search failed: {result.error}")

    print("\n3. Testing functional interface...")
    result = multi_search("quantum computing", num_queries=2, verbose=True)
    print(f"   Success: {result.success}")

    print("\nAll tests complete!")


if __name__ == "__main__":
    _test_multi_search()
