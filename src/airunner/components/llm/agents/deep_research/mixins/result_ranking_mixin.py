"""Result ranking mixin for DeepResearchAgent.

Handles LLM-based ranking of search results by relevance.
"""

import logging
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class ResultRankingMixin:
    """Provides LLM-based result ranking methods."""

    def _rank_results_with_llm(
        self, results: list, topic: str, max_results: int = 15
    ) -> list:
        """Use LLM to rank search results by relevance, ignoring search engine rank.

        Args:
            results: List of search results with title, url, snippet
            topic: Research topic
            max_results: Number of top results to return

        Returns:
            Top N most relevant results as determined by LLM
        """
        if not results:
            return []

        if len(results) <= max_results:
            return results

        # Build results text for LLM
        results_text = self._format_results_for_ranking(results)

        # Create ranking prompt
        prompt = self._build_ranking_prompt(
            topic, len(results), max_results, results_text
        )

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            ranking_text = response.content.strip()

            # Parse and validate indices
            selected_indices = self._parse_ranking_response(
                ranking_text, len(results)
            )

            if not selected_indices:
                logger.warning(
                    "[Phase 1A] LLM ranking returned no valid indices, using top results"
                )
                return results[:max_results]

            # Return results in LLM-ranked order
            ranked = [results[i] for i in selected_indices[:max_results]]
            logger.info(
                f"[Phase 1A] LLM selected indices: {selected_indices[:max_results]}"
            )
            return ranked

        except Exception as e:
            logger.error(
                f"[Phase 1A] LLM ranking failed: {e}, using top results"
            )
            return results[:max_results]

    def _format_results_for_ranking(self, results: list) -> list:
        """Format search results for LLM ranking.

        Args:
            results: List of search results

        Returns:
            List of formatted result strings
        """
        results_text = []
        for i, item in enumerate(results, 1):
            title = item.get("title", "No title")
            snippet = item.get("snippet", "")[:150]  # Truncate snippets
            url = item.get("link") or item.get("url", "")
            results_text.append(f"{i}. {title}\n   {snippet}\n   {url}")
        return results_text

    def _build_ranking_prompt(
        self,
        topic: str,
        num_results: int,
        max_results: int,
        results_text: list,
    ) -> str:
        """Build LLM prompt for ranking results.

        Args:
            topic: Research topic
            num_results: Total number of results
            max_results: Max results to return
            results_text: Formatted results

        Returns:
            Ranking prompt
        """
        return f"""You are evaluating search results for research on: "{topic}"

Rank these {num_results} search results by relevance to the topic. Return ONLY the numbers of the top {max_results} most relevant results, separated by commas.

Ignore the original search ranking - focus on ACTUAL RELEVANCE to "{topic}":
- Personal websites, official sites, and primary sources are often MORE relevant than news aggregators
- Direct information about the topic is better than tangential mentions
- Quality and specificity matter more than search rank

SEARCH RESULTS:
{chr(10).join(results_text[:50])}  

Return ONLY comma-separated numbers of the top {max_results} most relevant results (e.g., "13,7,42,3,19,28..."):"""

    def _parse_ranking_response(
        self, ranking_text: str, max_index: int
    ) -> list:
        """Parse LLM ranking response into list of indices.

        Args:
            ranking_text: LLM response with comma-separated numbers
            max_index: Maximum valid index

        Returns:
            List of valid result indices
        """
        try:
            selected_indices = [
                int(x.strip()) - 1
                for x in ranking_text.split(",")
                if x.strip().isdigit()
            ]
            # Filter to valid indices
            selected_indices = [
                i for i in selected_indices if 0 <= i < max_index
            ]
            return selected_indices
        except Exception as e:
            logger.warning(f"[Phase 1A] Failed to parse LLM ranking: {e}")
            return []

    def _validate_content_relevance(
        self, title: str, snippet: str, topic: str
    ) -> bool:
        """Use LLM to validate if search result is actually about the topic.

        Args:
            title: Search result title
            snippet: Search result snippet
            topic: Research topic

        Returns:
            True if content is relevant, False otherwise
        """
        prompt = f"""Is this search result relevant to researching: "{topic}"?

TITLE: {title}
SNIPPET: {snippet}

The result is relevant if it discusses the topic, related people, events, or context.
Answer ONLY "YES" if relevant, or "NO" if completely unrelated.
Do not explain - just answer YES or NO."""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            answer = response.content.strip().upper()

            is_relevant = "YES" in answer
            if not is_relevant:
                logger.info(
                    f"[LLM Filter] Rejected irrelevant result: {title[:50]}"
                )
            return is_relevant

        except Exception as e:
            logger.warning(
                f"[LLM Filter] Failed to validate relevance, allowing through: {e}"
            )
            # If LLM fails, fall back to allowing it (conservative approach)
            return True
