"""QA (question answering) tool registrations."""

from typing import List

from airunner_services.llm.core.tool_registry import ToolCategory, tool
from airunner_services.llm.tools.qa_tools_helpers import (
    extract_answer_from_context_impl,
    generate_clarifying_questions_impl,
    identify_answer_type_impl,
    rank_answer_candidates_impl,
    score_answer_confidence_impl,
    verify_answer_impl,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.application.log_hygiene import summarize_text

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="verify_answer",
    category=ToolCategory.QA,
    description=(
        "Verify the accuracy of an answer by checking it against known facts "
        "or retrieved context. Returns confidence score and supporting/"
        "contradicting evidence."
    ),
)
def verify_answer(question: str, answer: str, context: str = "") -> str:
    """Verify answer accuracy against optional context."""
    logger.info(
        "Verifying answer for question (%s)",
        summarize_text(question, label="question"),
    )
    return verify_answer_impl(question, answer, context)


@tool(
    name="score_answer_confidence",
    category=ToolCategory.QA,
    description=(
        "Score confidence level of an answer based on available evidence, "
        "source quality, and internal consistency. Returns score from 0-100."
    ),
)
def score_answer_confidence(
    answer: str,
    sources: List[str] | None = None,
    reasoning: str = "",
) -> str:
    """Score answer confidence using simple QA heuristics."""
    logger.info("Scoring answer confidence")
    return score_answer_confidence_impl(answer, sources, reasoning)


@tool(
    name="extract_answer_from_context",
    category=ToolCategory.QA,
    description=(
        "Extract a direct answer to a question from provided context. "
        "Useful for reading comprehension and information extraction tasks."
    ),
)
def extract_answer_from_context(question: str, context: str) -> str:
    """Extract a direct answer from the provided context."""
    logger.info(
        "Extracting answer for question (%s)",
        summarize_text(question, label="question"),
    )
    return extract_answer_from_context_impl(question, context)


@tool(
    name="generate_clarifying_questions",
    category=ToolCategory.QA,
    description=(
        "Generate clarifying questions to better understand an ambiguous "
        "query. Helps narrow down user intent and gather more specific "
        "information."
    ),
)
def generate_clarifying_questions(query: str, num_questions: int = 3) -> str:
    """Generate clarifying questions for an ambiguous query."""
    logger.info("Generating %s clarifying questions", num_questions)
    return generate_clarifying_questions_impl(query, num_questions)


@tool(
    name="rank_answer_candidates",
    category=ToolCategory.QA,
    description=(
        "Rank multiple candidate answers to a question based on relevance, "
        "accuracy, and completeness. Returns ranked list with scores."
    ),
)
def rank_answer_candidates(question: str, candidates: List[str]) -> str:
    """Rank answer candidates for a question."""
    logger.info("Ranking %s answer candidates", len(candidates))
    return rank_answer_candidates_impl(question, candidates)


@tool(
    name="identify_answer_type",
    category=ToolCategory.QA,
    description=(
        "Identify what type of answer is expected for a question "
        "(e.g., person, place, date, number, yes/no, explanation). "
        "Helps route questions to appropriate answering strategies."
    ),
)
def identify_answer_type(question: str) -> str:
    """Identify the expected answer type for a question."""
    logger.info("Identifying answer type")
    return identify_answer_type_impl(question)
