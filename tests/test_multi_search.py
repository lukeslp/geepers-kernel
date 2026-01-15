"""
Tests for multi-search utilities.
"""
import pytest
from unittest.mock import Mock, patch
from shared.utils.multi_search import (
    MultiSearchOrchestrator,
    SearchQuery,
    SearchResult,
    MultiSearchResult,
    multi_search
)


class TestSearchQuery:
    """Test SearchQuery dataclass."""

    def test_search_query_structure(self):
        """Test SearchQuery has expected attributes."""
        query = SearchQuery(
            text="machine learning trends",
            index=1,
            total=5,
            metadata={"source": "user"}
        )

        assert query.text == "machine learning trends"
        assert query.index == 1
        assert query.total == 5
        assert query.metadata["source"] == "user"


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_search_result_success(self):
        """Test successful SearchResult."""
        query = SearchQuery(text="test", index=1, total=1)
        result = SearchResult(
            query=query,
            content="Test content",
            success=True
        )

        assert result.success is True
        assert result.content == "Test content"
        assert result.error is None

    def test_search_result_error(self):
        """Test SearchResult with error."""
        query = SearchQuery(text="test", index=1, total=1)
        result = SearchResult(
            query=query,
            content="",
            success=False,
            error="API error"
        )

        assert result.success is False
        assert result.error == "API error"


class TestMultiSearchOrchestrator:
    """Test MultiSearchOrchestrator class."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        orchestrator = MultiSearchOrchestrator(api_key="test-key")
        assert orchestrator.api_key == "test-key"
        assert orchestrator.num_queries == 5
        assert orchestrator.max_workers == 5

    def test_init_without_api_key_raises(self):
        """Test initialization without API key raises ValueError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                MultiSearchOrchestrator()

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        orchestrator = MultiSearchOrchestrator(
            api_key="test-key",
            num_queries=3,
            max_workers=2,
            query_model="custom-model"
        )

        assert orchestrator.num_queries == 3
        assert orchestrator.max_workers == 2
        assert orchestrator.query_model == "custom-model"

    @patch('shared.utils.multi_search.requests.post')
    def test_generate_queries(self, mock_post):
        """Test query generation."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '["query 1", "query 2", "query 3"]'
                }
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        orchestrator = MultiSearchOrchestrator(api_key="test-key", num_queries=3)
        queries = orchestrator._generate_queries("AI safety")

        assert len(queries) <= 3
        assert mock_post.called

    @patch('shared.utils.multi_search.requests.post')
    def test_execute_single_search(self, mock_post):
        """Test single search execution."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Search result content"
                }
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        orchestrator = MultiSearchOrchestrator(api_key="test-key")
        result = orchestrator._execute_single_search("test query", 1, 1)

        assert result.success is True
        assert "Search result content" in result.content

    @patch('shared.utils.multi_search.requests.post')
    def test_search_with_callbacks(self, mock_post):
        """Test search with progress callbacks."""
        # Mock API responses
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '["query 1", "query 2"]'
                }
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        queries_generated = []
        searches_completed = []
        synthesis_started = []

        def on_queries(q):
            queries_generated.append(len(q))

        def on_search(r):
            searches_completed.append(r)

        def on_synthesis():
            synthesis_started.append(True)

        orchestrator = MultiSearchOrchestrator(api_key="test-key", num_queries=2)

        with patch.object(orchestrator, '_generate_queries', return_value=["q1", "q2"]):
            with patch.object(orchestrator, '_execute_searches', return_value=[]):
                with patch.object(orchestrator, '_synthesize_report', return_value="Final report"):
                    result = orchestrator.search(
                        "test topic",
                        on_queries_generated=on_queries,
                        on_search_complete=on_search,
                        on_synthesis_start=on_synthesis
                    )

        assert len(queries_generated) > 0
        assert len(synthesis_started) > 0


class TestFunctionalInterface:
    """Test functional interface convenience functions."""

    @patch('shared.utils.multi_search.MultiSearchOrchestrator')
    def test_multi_search_function(self, mock_orchestrator_class):
        """Test multi_search convenience function."""
        mock_orchestrator = Mock()
        mock_result = MultiSearchResult(
            original_query="test",
            generated_queries=["q1", "q2"],
            search_results=[],
            final_report="Report",
            success=True
        )
        mock_orchestrator.search.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        result = multi_search("test topic", api_key="test-key", num_queries=2)

        assert result.success is True
        assert mock_orchestrator.search.called


class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch('shared.utils.multi_search.requests.post')
    def test_api_error_handling(self, mock_post):
        """Test handling of API errors."""
        mock_post.side_effect = Exception("Network error")

        orchestrator = MultiSearchOrchestrator(api_key="test-key")
        result = orchestrator.search("test topic")

        assert result.success is False
        assert "Network error" in result.error

    def test_empty_query_extraction(self):
        """Test handling when no queries extracted."""
        orchestrator = MultiSearchOrchestrator(api_key="test-key")

        # Mock response with no extractable queries
        response = {"choices": [{"message": {"content": "Invalid response"}}]}
        queries = orchestrator._extract_queries_from_response(response)

        assert isinstance(queries, list)

    @patch('shared.utils.multi_search.requests.post')
    def test_partial_search_failure(self, mock_post):
        """Test handling when some searches fail."""
        # First call succeeds (query generation)
        # Subsequent calls fail (searches)
        mock_response_success = Mock()
        mock_response_success.json.return_value = {
            "choices": [{"message": {"content": '["q1", "q2"]'}}]
        }
        mock_response_success.raise_for_status = Mock()

        mock_post.side_effect = [
            mock_response_success,
            Exception("Search 1 failed"),
            mock_response_success
        ]

        orchestrator = MultiSearchOrchestrator(api_key="test-key", num_queries=2)
        orchestrator.search("test")

        # Should still attempt to complete despite partial failures
        assert mock_post.call_count >= 1
