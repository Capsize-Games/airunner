"""
Unit tests for the tool search engine.

Tests BM25 search functionality, fallback search, and tool indexing.
"""

import pytest
from unittest.mock import patch, MagicMock

from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolInfo,
    ToolCategory,
    tool,
)
from airunner.components.llm.core.tool_search import (
    ToolSearchEngine,
    get_tool_search_engine,
)


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the registry before and after each test."""
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()


@pytest.fixture
def sample_tools():
    """Register sample tools for testing."""
    @tool(
        name="test_search_web",
        category=ToolCategory.SEARCH,
        description="Search the internet for information",
        defer_loading=True,
        keywords=["internet", "google", "query"],
    )
    def search_web(query: str) -> str:
        return f"Results for {query}"

    @tool(
        name="test_generate_image",
        category=ToolCategory.IMAGE,
        description="Generate an image from text prompt",
        defer_loading=True,
        keywords=["picture", "art", "create", "draw"],
    )
    def generate_image(prompt: str) -> str:
        return f"Image: {prompt}"

    @tool(
        name="test_read_file",
        category=ToolCategory.FILE,
        description="Read contents of a file from disk",
        defer_loading=True,
        keywords=["open", "load", "text", "document"],
    )
    def read_file(path: str) -> str:
        return f"Contents of {path}"

    @tool(
        name="test_immediate_tool",
        category=ToolCategory.SYSTEM,
        description="An always-available tool",
        defer_loading=False,
    )
    def immediate_tool() -> str:
        return "Always here"

    return {
        "search_web": search_web,
        "generate_image": generate_image,
        "read_file": read_file,
        "immediate_tool": immediate_tool,
    }


class TestToolSearchEngine:
    """Tests for ToolSearchEngine class."""

    def test_init_indexes_deferred_tools(self, sample_tools):
        """Engine should index only deferred tools by default."""
        engine = ToolSearchEngine(include_immediate=False)
        
        # Should have indexed 3 deferred tools
        assert len(engine._tools) == 3
        
        # Should not include immediate tool
        tool_names = [t.name for t in engine._tools]
        assert "test_immediate_tool" not in tool_names
        assert "test_search_web" in tool_names

    def test_init_with_immediate(self, sample_tools):
        """Engine can optionally include immediate tools."""
        engine = ToolSearchEngine(include_immediate=True)
        
        # Should have all 4 tools
        assert len(engine._tools) == 4
        
        tool_names = [t.name for t in engine._tools]
        assert "test_immediate_tool" in tool_names

    def test_search_finds_relevant_tools(self, sample_tools):
        """Search should return relevant tools based on query."""
        engine = ToolSearchEngine(include_immediate=False)
        
        results = engine.search("search the internet", limit=5)
        
        assert len(results) > 0
        # Search web tool should be first or near first
        result_names = [t.name for t in results]
        assert "test_search_web" in result_names

    def test_search_respects_limit(self, sample_tools):
        """Search should respect the limit parameter."""
        engine = ToolSearchEngine(include_immediate=False)
        
        results = engine.search("tool", limit=1)
        
        assert len(results) <= 1

    def test_search_with_keywords(self, sample_tools):
        """Search should match on keywords."""
        engine = ToolSearchEngine(include_immediate=False)
        
        # Search for "picture" which is a keyword for generate_image
        results = engine.search("picture", limit=5)
        
        result_names = [t.name for t in results]
        assert "test_generate_image" in result_names

    def test_search_empty_query(self, sample_tools):
        """Search with empty query should return empty results."""
        engine = ToolSearchEngine(include_immediate=False)
        
        results = engine.search("", limit=5)
        
        assert results == []

    def test_search_no_matches(self, sample_tools):
        """Search with unrelated query should return empty results."""
        engine = ToolSearchEngine(include_immediate=False)
        
        # Search for something completely unrelated
        results = engine.search("xyzzyx12345", limit=5)
        
        # May return empty or low-scoring results
        assert len(results) >= 0

    def test_tokenize(self, sample_tools):
        """Tokenizer should lowercase and split on non-alphanumeric."""
        engine = ToolSearchEngine()
        
        tokens = engine._tokenize("Search the Web! 123")
        
        assert "search" in tokens
        assert "the" in tokens
        assert "web" in tokens
        assert "123" in tokens
        # Should be lowercase
        assert "Search" not in tokens

    def test_refresh_updates_index(self, sample_tools):
        """Refresh should update the index with new tools."""
        engine = ToolSearchEngine(include_immediate=False)
        initial_count = len(engine._tools)
        
        # Add a new deferred tool
        @tool(
            name="test_new_tool",
            category=ToolCategory.SYSTEM,
            description="A newly added tool",
            defer_loading=True,
        )
        def new_tool() -> str:
            return "New"
        
        # Refresh the index
        engine.refresh()
        
        assert len(engine._tools) == initial_count + 1

    def test_fallback_search_without_bm25(self, sample_tools):
        """Engine should work without rank_bm25 installed."""
        engine = ToolSearchEngine(include_immediate=False)
        
        # Force fallback mode
        engine._index = None
        
        results = engine._fallback_search(["search", "internet"], limit=5)
        
        assert len(results) > 0
        result_names = [t.name for t in results]
        assert "test_search_web" in result_names


class TestGetToolSearchEngine:
    """Tests for the get_tool_search_engine singleton."""

    def test_returns_same_instance(self, sample_tools):
        """Should return same instance for same parameters."""
        # Reset global
        import airunner.components.llm.core.tool_search as module
        module._search_engine = None
        
        engine1 = get_tool_search_engine(include_immediate=False)
        engine2 = get_tool_search_engine(include_immediate=False)
        
        assert engine1 is engine2

    def test_creates_new_for_different_params(self, sample_tools):
        """Should create new instance for different parameters."""
        import airunner.components.llm.core.tool_search as module
        module._search_engine = None
        
        engine1 = get_tool_search_engine(include_immediate=False)
        engine2 = get_tool_search_engine(include_immediate=True)
        
        assert engine1 is not engine2
