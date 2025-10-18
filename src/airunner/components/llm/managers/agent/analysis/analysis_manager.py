"""
Analysis manager that orchestrates multiple conversation analyzers.

Runs analyzers in parallel (or sequentially), collects results,
and builds comprehensive conversation context.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from airunner.components.llm.managers.agent.analysis.base_analyzer import (
    BaseAnalyzer,
    AnalysisResult,
)


@dataclass
class ConversationContext:
    """
    Comprehensive context about the conversation state.

    This feeds back into response generation to make bot more realistic.
    """

    # Core identifiers
    user_message: str = ""
    bot_response: str = ""
    message_count: int = 0

    # Analysis results
    mood: Dict[str, Any] = field(default_factory=dict)
    sentiment: Dict[str, Any] = field(default_factory=dict)
    relationship: Dict[str, Any] = field(default_factory=dict)

    # Future analyzers can add more fields:
    # engagement_level: Dict[str, Any] = field(default_factory=dict)
    # topic_tracking: Dict[str, Any] = field(default_factory=dict)
    # personality_alignment: Dict[str, Any] = field(default_factory=dict)

    # Meta
    analysis_timestamp: Optional[str] = None
    raw_results: Dict[str, AnalysisResult] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_count": self.message_count,
            "mood": self.mood,
            "sentiment": self.sentiment,
            "relationship": self.relationship,
            "analysis_timestamp": self.analysis_timestamp,
        }


class AnalysisManager:
    """
    Manages multiple conversation analyzers.

    Orchestrates analysis pipeline and builds comprehensive context.
    """

    def __init__(
        self,
        analyzers: Optional[List[BaseAnalyzer]] = None,
        parallel: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize analysis manager.

        Args:
            analyzers: List of analyzer instances
            parallel: Run analyzers in parallel (faster but more resources)
            logger: Logger instance
        """
        self.analyzers = analyzers or []
        self.parallel = parallel
        self.logger = logger or logging.getLogger(__name__)

        # Context persistence
        self._current_context: Optional[ConversationContext] = None
        self._message_count = 0

    def add_analyzer(self, analyzer: BaseAnalyzer):
        """Add an analyzer to the pipeline."""
        self.analyzers.append(analyzer)
        self.logger.info(f"Added analyzer: {analyzer.name}")

    def remove_analyzer(self, name: str) -> bool:
        """Remove an analyzer by name."""
        original_count = len(self.analyzers)
        self.analyzers = [a for a in self.analyzers if a.name != name]
        removed = len(self.analyzers) < original_count
        if removed:
            self.logger.info(f"Removed analyzer: {name}")
        return removed

    def analyze(
        self,
        user_message: str,
        bot_response: str,
        llm_callable: Callable,
        conversation_history: Optional[list] = None,
    ) -> ConversationContext:
        """
        Run all analyzers and build conversation context.

        Args:
            user_message: Latest user message
            bot_response: Latest bot response
            llm_callable: Function to call LLM
            conversation_history: Previous messages

        Returns:
            ConversationContext with all analysis results
        """
        self._message_count += 1

        # Build context for analyzers
        analyzer_context = self._build_analyzer_context()

        # Determine which analyzers should run
        active_analyzers = [
            a for a in self.analyzers if a.should_run(analyzer_context)
        ]

        self.logger.info(
            f"Running {len(active_analyzers)}/{len(self.analyzers)} analyzers"
        )

        # Run analyzers
        if self.parallel and len(active_analyzers) > 1:
            results = self._run_parallel(
                active_analyzers,
                user_message,
                bot_response,
                llm_callable,
                conversation_history,
                analyzer_context,
            )
        else:
            results = self._run_sequential(
                active_analyzers,
                user_message,
                bot_response,
                llm_callable,
                conversation_history,
                analyzer_context,
            )

        # Build conversation context from results
        context = self._build_conversation_context(
            user_message, bot_response, results
        )

        # Update persistent context
        self._current_context = context

        return context

    def _build_analyzer_context(self) -> Dict[str, Any]:
        """Build context dictionary for analyzers."""
        context = {
            "message_count": self._message_count,
        }

        if self._current_context:
            context["current_mood"] = self._current_context.mood
            context["current_relationship"] = (
                self._current_context.relationship
            )
            # Add more as needed

        return context

    def _run_sequential(
        self,
        analyzers: List[BaseAnalyzer],
        user_message: str,
        bot_response: str,
        llm_callable: Callable,
        conversation_history: Optional[list],
        context: Dict[str, Any],
    ) -> Dict[str, AnalysisResult]:
        """Run analyzers sequentially."""
        results = {}

        for analyzer in analyzers:
            try:
                result = analyzer.analyze(
                    user_message,
                    bot_response,
                    llm_callable,
                    conversation_history,
                    context,
                )
                results[analyzer.name] = result

                if not result.success:
                    self.logger.warning(
                        f"Analyzer {analyzer.name} failed: {result.error}"
                    )

            except Exception as e:
                self.logger.error(
                    f"Analyzer {analyzer.name} crashed: {e}", exc_info=True
                )

        return results

    def _run_parallel(
        self,
        analyzers: List[BaseAnalyzer],
        user_message: str,
        bot_response: str,
        llm_callable: Callable,
        conversation_history: Optional[list],
        context: Dict[str, Any],
    ) -> Dict[str, AnalysisResult]:
        """Run analyzers in parallel."""
        results = {}

        with ThreadPoolExecutor(max_workers=len(analyzers)) as executor:
            future_to_analyzer = {
                executor.submit(
                    analyzer.analyze,
                    user_message,
                    bot_response,
                    llm_callable,
                    conversation_history,
                    context,
                ): analyzer
                for analyzer in analyzers
            }

            for future in as_completed(future_to_analyzer):
                analyzer = future_to_analyzer[future]
                try:
                    result = future.result()
                    results[analyzer.name] = result

                    if not result.success:
                        self.logger.warning(
                            f"Analyzer {analyzer.name} failed: {result.error}"
                        )

                except Exception as e:
                    self.logger.error(
                        f"Analyzer {analyzer.name} crashed: {e}",
                        exc_info=True,
                    )

        return results

    def _build_conversation_context(
        self,
        user_message: str,
        bot_response: str,
        results: Dict[str, AnalysisResult],
    ) -> ConversationContext:
        """Build ConversationContext from analysis results."""
        from datetime import datetime

        context = ConversationContext(
            user_message=user_message,
            bot_response=bot_response,
            message_count=self._message_count,
            analysis_timestamp=datetime.now().isoformat(),
            raw_results=results,
        )

        # Extract data from successful results
        for name, result in results.items():
            if result.success and result.data:
                if name == "mood":
                    context.mood = result.data
                elif name == "sentiment":
                    context.sentiment = result.data
                elif name == "relationship":
                    context.relationship = result.data
                # Add more mappings as analyzers are added

        return context

    def get_current_context(self) -> Optional[ConversationContext]:
        """Get the most recent conversation context."""
        return self._current_context

    def reset(self):
        """Reset context state."""
        self._current_context = None
        self._message_count = 0
        self.logger.info("Analysis context reset")
