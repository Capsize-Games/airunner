"""
Tool search engine for on-demand tool discovery.

Provides BM25-based search over tool names, descriptions, and keywords
to enable dynamic tool loading and reduce initial context size.
"""

import re
from typing import List, Optional

from airunner.components.llm.core.tool_registry import ToolRegistry, ToolInfo
from airunner.utils.application import get_logger


logger = get_logger(__name__)


class ToolSearchEngine:
    """BM25 + regex search engine for tool discovery.
    
    This engine indexes deferred tools (defer_loading=True) and allows
    semantic search to discover relevant tools on-demand, reducing the
    initial context token count by up to 96%.
    
    Attributes:
        _index: BM25Okapi index for ranked search
        _tools: List of indexed ToolInfo objects
        _corpus: Tokenized corpus for BM25
    """

    def __init__(self, include_immediate: bool = False):
        """Initialize the search engine.
        
        Args:
            include_immediate: If True, also index immediate tools.
                Default is False (only deferred tools).
        """
        self._index = None
        self._tools: List[ToolInfo] = []
        self._corpus: List[List[str]] = []
        self._include_immediate = include_immediate
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25 indexing.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of lowercase tokens
        """
        # Convert to lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
        return tokens

    def _build_index(self) -> None:
        """Build BM25 index from tool metadata.
        
        Indexes tool names, descriptions, categories, and keywords
        for semantic search.
        """
        # Get tools to index
        if self._include_immediate:
            tools_dict = ToolRegistry.all()
        else:
            tools_dict = ToolRegistry.get_deferred_tools()
        
        self._tools = list(tools_dict.values())
        
        if not self._tools:
            logger.debug("No tools to index for search engine")
            return
        
        # Build corpus from tool metadata
        self._corpus = []
        for tool in self._tools:
            # Combine all searchable text
            text_parts = [
                tool.name.replace("_", " "),
                tool.description,
                tool.category.value,
            ]
            # Add keywords
            text_parts.extend(tool.keywords)
            
            # Tokenize combined text
            combined_text = " ".join(text_parts)
            tokens = self._tokenize(combined_text)
            self._corpus.append(tokens)
        
        # Try to use rank_bm25 if available, otherwise fall back to simple search
        try:
            from rank_bm25 import BM25Okapi
            self._index = BM25Okapi(self._corpus)
            logger.debug(f"Built BM25 index with {len(self._tools)} tools")
        except ImportError:
            logger.warning(
                "rank_bm25 not installed. Using fallback text search. "
                "Install with: pip install rank-bm25"
            )
            self._index = None

    def search(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> List[ToolInfo]:
        """Search for tools matching the query.
        
        Args:
            query: Natural language search query
            limit: Maximum number of results to return
            min_score: Minimum BM25 score to include (0.0 includes all matches)
            
        Returns:
            List of matching ToolInfo objects, ranked by relevance
        """
        if not self._tools:
            # Rebuild index if empty (tools may have been registered since init)
            self._build_index()
            if not self._tools:
                return []
        
        tokens = self._tokenize(query)
        
        if not tokens:
            return []
        
        if self._index is not None:
            # Use BM25 ranking
            scores = self._index.get_scores(tokens)
            
            # Pair tools with scores and filter by minimum score
            ranked = [
                (tool, score) 
                for tool, score in zip(self._tools, scores)
                if score > min_score
            ]
            
            # Sort by score descending
            ranked.sort(key=lambda x: -x[1])
            
            return [tool for tool, _ in ranked[:limit]]
        else:
            # Fallback: simple keyword matching
            return self._fallback_search(tokens, limit)

    def _fallback_search(
        self,
        query_tokens: List[str],
        limit: int,
    ) -> List[ToolInfo]:
        """Fallback search using simple keyword matching.
        
        Used when rank_bm25 is not available.
        
        Args:
            query_tokens: Tokenized query
            limit: Maximum results
            
        Returns:
            List of matching tools
        """
        query_set = set(query_tokens)
        
        results = []
        for tool, corpus_tokens in zip(self._tools, self._corpus):
            corpus_set = set(corpus_tokens)
            # Count matching tokens
            matches = len(query_set & corpus_set)
            if matches > 0:
                results.append((tool, matches))
        
        # Sort by match count descending
        results.sort(key=lambda x: -x[1])
        
        return [tool for tool, _ in results[:limit]]

    def refresh(self) -> None:
        """Refresh the search index.
        
        Call this after new tools are registered to include them in search.
        """
        self._build_index()


# Global search engine instance (lazy initialized)
_search_engine: Optional[ToolSearchEngine] = None


def get_tool_search_engine(include_immediate: bool = False) -> ToolSearchEngine:
    """Get the global tool search engine instance.
    
    Args:
        include_immediate: If True, also search immediate tools
        
    Returns:
        ToolSearchEngine instance
    """
    global _search_engine
    
    if _search_engine is None or _search_engine._include_immediate != include_immediate:
        _search_engine = ToolSearchEngine(include_immediate=include_immediate)
    
    return _search_engine
