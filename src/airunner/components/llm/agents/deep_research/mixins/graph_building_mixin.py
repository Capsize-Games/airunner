"""
Graph Building Mixin - Handles LangGraph construction and compilation.

This mixin provides graph building functionality for the Deep Research Agent:
- Graph structure definition
- Node and edge configuration
- Graph compilation
"""

import re
from typing import Any
from langgraph.graph import START, END, StateGraph
from typing_extensions import TypedDict

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class GraphBuildingMixin:
    """Mixin for graph building in Deep Research Agent."""

    @staticmethod
    def _parse_research_prompt(user_prompt: str) -> str:
        """Parse user prompt to extract actual research topic.

        Removes meta-instructions and command words that shouldn't be
        treated as literal search terms. Prevents issues like treating
        "Tell Me What is Going" as a platform name.

        Args:
            user_prompt: Raw user input

        Returns:
            Cleaned research topic suitable for searches
        """
        cleaned = user_prompt.strip()
        lower = cleaned.lower()

        command_prefixes = [
            "research ",
            "analyze ",
            "investigate ",
            "study ",
            "examine ",
            "explore ",
            "look into ",
            "find out about ",
            "tell me about ",
            "tell me what is going on with ",
            "what is going on with ",
            "explain ",
            "give me information on ",
            "give me info on ",
            "i want to know about ",
            "i need information on ",
        ]

        for prefix in command_prefixes:
            if lower.startswith(prefix):
                cleaned = cleaned[len(prefix) :]
                lower = lower[len(prefix) :]
                break

        trailing_patterns = [
            r"\s+pay special attention to\s+.+$",
            r"\s+is the government\s+.+\?$",
            r"\s+why do they\s+.+\?$",
        ]

        for pattern in trailing_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        cleaned = " ".join(cleaned.split())
        return cleaned

    @staticmethod
    def _generate_professional_title(user_prompt: str) -> str:
        """Generate a professional research title from user prompt.

        Args:
            user_prompt: Raw user prompt

        Returns:
            Professional title
        """
        prompt_lower = user_prompt.lower()

        for prefix in [
            "research ",
            "analyze ",
            "investigate ",
            "study ",
            "examine ",
        ]:
            if prompt_lower.startswith(prefix):
                prompt_lower = prompt_lower[len(prefix) :]
                break

        words = prompt_lower.split()
        skip_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
        }

        title_words = [
            (
                word.capitalize()
                if i == 0 or word not in skip_words or len(word) > 4
                else word
            )
            for i, word in enumerate(words)
        ]

        base_title = " ".join(title_words)

        if any(
            keyword in prompt_lower
            for keyword in [
                "decision",
                "policy",
                "action",
                "order",
                "sanctions",
            ]
        ):
            return f"{base_title}: Recent Developments and Policy Analysis"
        elif any(
            keyword in prompt_lower
            for keyword in ["impact", "effect", "consequence", "implication"]
        ):
            return f"{base_title}: Analysis and Implications"
        else:
            return f"{base_title}: A Research Analysis"

    def build_graph(self) -> StateGraph:
        """Build the Deep Research agent graph with explicit phases.

        Each phase handles its own tool loops internally via _execute_phase_with_tools(),
        so the graph is purely linear.

        Returns:
            StateGraph for deep research mode
        """
        logger.info(
            "Building Deep Research agent graph (phase-based workflow)"
        )

        # Import here to avoid circular imports
        from airunner.components.llm.agents.deep_research.deep_research_agent import (
            DeepResearchState,
        )

        graph = StateGraph(DeepResearchState)

        # Add all phase nodes
        graph.add_node("plan", self._plan_research)
        graph.add_node("phase0", self._phase0_rag_check)
        graph.add_node("phase1a", self._phase1a_gather)
        graph.add_node("phase1a_curiosity", self._phase1a_curiosity)
        graph.add_node("phase1b", self._phase1b_analyze)
        graph.add_node("phase1b_thesis", self._phase1b_thesis)
        graph.add_node("phase1c", self._phase1c_outline)
        graph.add_node("phase1d", self._phase1d_write)
        graph.add_node("phase1e", self._phase1e_review)
        graph.add_node("phase1f", self._phase1f_revise)
        graph.add_node("finalize", self._finalize_document)

        # Pure linear progression
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "phase0")
        graph.add_edge("phase0", "phase1a")
        graph.add_edge("phase1a", "phase1b")
        graph.add_edge("phase1b", "phase1b_thesis")
        graph.add_edge("phase1b_thesis", "phase1c")
        graph.add_edge("phase1c", "phase1d")
        graph.add_edge("phase1d", "phase1e")
        graph.add_edge("phase1e", "phase1f")
        graph.add_edge("phase1f", "finalize")
        graph.add_edge("finalize", END)

        logger.info(
            "Deep Research agent graph built successfully (curiosity phase DISABLED to prevent hallucination)"
        )
        return graph

    def compile(self) -> Any:
        """Build and compile the Deep Research agent graph.

        Returns:
            Compiled graph ready for invocation
        """
        graph = self.build_graph()
        compiled = graph.compile()
        logger.info("Deep Research agent compiled successfully")
        return compiled
