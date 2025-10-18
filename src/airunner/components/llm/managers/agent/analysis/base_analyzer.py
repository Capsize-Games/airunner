"""
Base analyzer for conversation analysis pipeline.

Each analyzer performs a specific analysis task (mood, sentiment, intent, etc.)
with its own specialized prompt and LLM settings.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable
import logging


@dataclass
class AnalyzerConfig:
    """Configuration for an analyzer's LLM call."""

    temperature: float = 0.3
    max_new_tokens: int = 200
    min_new_tokens: int = 16
    top_p: float = 0.9
    top_k: int = 10
    do_sample: bool = True
    repetition_penalty: float = 1.0
    use_cache: bool = True
    # Custom fields for specific analyzers
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """Result from an analyzer."""

    analyzer_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    raw_response: Optional[str] = None


class BaseAnalyzer(ABC):
    """
    Base class for conversation analyzers.

    Each analyzer:
    - Has a specialized system prompt
    - Uses custom LLM generation settings
    - Processes conversation context
    - Returns structured results
    """

    def __init__(
        self,
        name: str,
        config: Optional[AnalyzerConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize analyzer.

        Args:
            name: Unique identifier for this analyzer
            config: LLM generation config (uses defaults if None)
            logger: Logger instance
        """
        self.name = name
        self.config = config or AnalyzerConfig()
        self.logger = logger or logging.getLogger(__name__)

    @abstractmethod
    def build_prompt(
        self,
        user_message: str,
        bot_response: str,
        conversation_history: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the specialized prompt for this analyzer.

        Args:
            user_message: Latest user message
            bot_response: Latest bot response
            conversation_history: Previous messages
            context: Additional context (bot personality, mood, etc.)

        Returns:
            Formatted prompt string
        """
        pass

    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured data.

        Args:
            response: Raw LLM output

        Returns:
            Dictionary with parsed data
        """
        pass

    def analyze(
        self,
        user_message: str,
        bot_response: str,
        llm_callable: Callable,
        conversation_history: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        Run the analysis.

        Args:
            user_message: Latest user message
            bot_response: Latest bot response
            llm_callable: Function to call LLM
            conversation_history: Previous messages
            context: Additional context

        Returns:
            AnalysisResult with structured data
        """
        try:
            # Build prompt
            prompt = self.build_prompt(
                user_message, bot_response, conversation_history, context
            )

            self.logger.debug(
                f"{self.name} analyzer: prompt length {len(prompt)} chars"
            )

            # Call LLM with analyzer-specific settings
            kwargs = {
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_new_tokens,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k,
                "do_sample": self.config.do_sample,
                "repetition_penalty": self.config.repetition_penalty,
                **self.config.extras,
            }

            response = llm_callable(prompt, **kwargs)
            response_text = (
                response.text if hasattr(response, "text") else str(response)
            )

            self.logger.debug(
                f"{self.name} analyzer: response length {len(response_text)} chars"
            )

            # Parse response
            parsed_data = self.parse_response(response_text)

            return AnalysisResult(
                analyzer_name=self.name,
                success=True,
                data=parsed_data,
                raw_response=response_text,
            )

        except Exception as e:
            self.logger.error(
                f"{self.name} analyzer failed: {e}", exc_info=True
            )
            return AnalysisResult(
                analyzer_name=self.name,
                success=False,
                error=str(e),
            )

    def should_run(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Determine if this analyzer should run.

        Can be overridden for conditional execution
        (e.g., only run every N messages, only on certain triggers).

        Args:
            context: Current context

        Returns:
            True if analyzer should run
        """
        return True
