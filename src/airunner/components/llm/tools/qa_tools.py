"""
QA (Question Answering) mode tools.

Provides tools for:
- Knowledge retrieval and recall
- Fact checking and verification
- Answer confidence scoring
- Source-grounded responses
"""

from typing import List
from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Note: RAG and knowledge tools are currently in rag_tools.py and knowledge_tools.py
# They will be migrated here or dual-registered in a future update
# For now we create complementary QA-specific tools


@tool(
    name="verify_answer",
    category=ToolCategory.QA,
    description=(
        "Verify the accuracy of an answer by checking it against known facts "
        "or retrieved context. Returns confidence score and supporting/contradicting evidence."
    ),
)
def verify_answer(question: str, answer: str, context: str = "") -> str:
    """
    Verify answer accuracy.

    Args:
        question: The original question
        answer: The answer to verify
        context: Optional context or retrieved facts to check against

    """
    logger.info(f"Verifying answer for question: {question[:50]}...")

    # Simple verification heuristics
    answer_lower = answer.lower()
    context_lower = context.lower() if context else ""

    # Check if key terms from answer appear in context
    answer_words = set(w for w in answer_lower.split() if len(w) > 4)
    context_words = set(w for w in context_lower.split() if len(w) > 4)

    if context:
        overlap = answer_words & context_words
        confidence = min(len(overlap) / max(len(answer_words), 1) * 100, 100)
    else:
        confidence = 50.0  # No context = uncertain

    return (
        f"Answer Verification:\n\n"
        f"Question: {question}\n"
        f"Answer: {answer[:200]}{'...' if len(answer) > 200 else ''}\n\n"
        f"Confidence: {confidence:.1f}%\n"
        f"Evidence: {f'Found {len(overlap)} supporting terms in context' if context else 'No context provided'}\n\n"
        + (
            f"Supporting context: {context[:200]}..."
            if context and confidence > 50
            else ""
        )
        + (
            f"\nWarning: Low confidence, answer may need verification"
            if confidence < 60
            else ""
        )
    )


@tool(
    name="score_answer_confidence",
    category=ToolCategory.QA,
    description=(
        "Score confidence level of an answer based on available evidence, "
        "source quality, and internal consistency. Returns score from 0-100."
    ),
)
def score_answer_confidence(
    answer: str, sources: List[str] = None, reasoning: str = ""
) -> str:
    """
    Score answer confidence.

    Args:
        answer: The answer to score
        sources: Optional list of sources supporting the answer
        reasoning: Optional reasoning chain that led to the answer

    """
    logger.info("Scoring answer confidence")

    sources = sources or []
    base_score = 50

    # Adjust based on sources
    if sources:
        base_score += min(len(sources) * 10, 30)

    # Adjust based on answer length/detail
    if len(answer.split()) > 50:
        base_score += 10  # Detailed answer

    # Adjust based on reasoning
    if reasoning and len(reasoning) > 100:
        base_score += 10  # Has reasoning chain

    confidence = min(base_score, 100)

    factors = []
    if sources:
        factors.append(f"✓ Supported by {len(sources)} source(s)")
    if len(answer.split()) > 50:
        factors.append("✓ Detailed answer provided")
    if reasoning:
        factors.append("✓ Reasoning chain available")
    if not sources:
        factors.append("⚠ No source verification")

    return (
        f"Answer Confidence Score: {confidence}/100\n\n"
        f"Factors:\n" + "\n".join(f"  {f}" for f in factors) + "\n\n"
        f"Recommendation: "
        + (
            "High confidence - answer well-supported"
            if confidence >= 80
            else (
                "Moderate confidence - verify if critical"
                if confidence >= 60
                else "Low confidence - additional verification needed"
            )
        )
    )


@tool(
    name="extract_answer_from_context",
    category=ToolCategory.QA,
    description=(
        "Extract a direct answer to a question from provided context. "
        "Useful for reading comprehension and information extraction tasks."
    ),
)
def extract_answer_from_context(question: str, context: str) -> str:
    """
    Extract answer from context.

    Args:
        question: The question to answer
        context: The context containing the answer

    """
    logger.info(f"Extracting answer for: {question[:50]}...")

    # Simple extraction: find sentences containing question keywords
    question_words = set(w.lower() for w in question.split() if len(w) > 3)

    sentences = context.replace("! ", ".|").replace("? ", ".|").split(".|")
    scored_sentences = []

    for sent in sentences:
        sent_words = set(w.lower() for w in sent.split())
        overlap = question_words & sent_words
        if overlap:
            score = len(overlap)
            scored_sentences.append((score, sent.strip()))

    if not scored_sentences:
        return f"Could not find answer to '{question}' in provided context."

    scored_sentences.sort(reverse=True)
    best_match = scored_sentences[0][1]

    return (
        f"Question: {question}\n\n"
        f"Extracted Answer: {best_match}\n\n"
        f"Confidence: {f'High ({scored_sentences[0][0]} matching terms)' if scored_sentences[0][0] > 2 else 'Moderate'}\n"
        f"Location: Found in context"
    )


@tool(
    name="generate_clarifying_questions",
    category=ToolCategory.QA,
    description=(
        "Generate clarifying questions to better understand an ambiguous query. "
        "Helps narrow down user intent and gather more specific information."
    ),
)
def generate_clarifying_questions(query: str, num_questions: int = 3) -> str:
    """
    Generate clarifying questions.

    Args:
        query: The ambiguous query
        num_questions: Number of clarifying questions to generate

    """
    logger.info(f"Generating {num_questions} clarifying questions")

    # Analyze query for ambiguities
    words = query.lower().split()

    questions = []

    # Check for pronouns (ambiguous references)
    if any(p in words for p in ["it", "this", "that", "they", "them"]):
        questions.append("What specifically are you referring to?")

    # Check for vague terms
    if any(v in words for v in ["thing", "stuff", "something", "some"]):
        questions.append(
            "Could you be more specific about what you're asking about?"
        )

    # Check for time ambiguity
    if any(t in words for t in ["recent", "latest", "new", "old"]):
        questions.append("What time period are you interested in?")

    # Add general questions if needed
    while len(questions) < num_questions:
        if len(questions) == 0:
            questions.append("What aspect of this topic interests you most?")
        elif len(questions) == 1:
            questions.append(
                "Are you looking for a specific type of information?"
            )
        else:
            questions.append(
                "Is there any context that would help me answer better?"
            )

    return f"Query: {query}\n\n" f"Clarifying Questions:\n" + "\n".join(
        f"{i}. {q}" for i, q in enumerate(questions[:num_questions], 1)
    )


@tool(
    name="rank_answer_candidates",
    category=ToolCategory.QA,
    description=(
        "Rank multiple candidate answers to a question based on relevance, "
        "accuracy, and completeness. Returns ranked list with scores."
    ),
)
def rank_answer_candidates(question: str, candidates: List[str]) -> str:
    """
    Rank answer candidates.

    Args:
        question: The question being answered
        candidates: List of candidate answers

    """
    logger.info(f"Ranking {len(candidates)} answer candidates")

    if not candidates:
        return "No candidates provided to rank."

    # Extract question keywords
    question_words = set(w.lower() for w in question.split() if len(w) > 3)

    # Score each candidate
    scored = []
    for i, candidate in enumerate(candidates):
        candidate_words = set(w.lower() for w in candidate.split())
        overlap = question_words & candidate_words

        # Simple scoring: keyword overlap + length bonus
        score = len(overlap) * 10
        if 20 < len(candidate.split()) < 100:  # Prefer moderate length
            score += 5

        scored.append((score, i, candidate))

    scored.sort(reverse=True)

    result = f"Question: {question}\n\nRanked Answers:\n\n"
    for rank, (score, orig_idx, candidate) in enumerate(scored, 1):
        result += (
            f"{rank}. [Score: {score}] {candidate[:150]}"
            f"{'...' if len(candidate) > 150 else ''}\n\n"
        )

    return result


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
    """
    Identify expected answer type.

    Args:
        question: The question to analyze

    """
    logger.info("Identifying answer type")

    question_lower = question.lower()

    # Question word patterns
    if question_lower.startswith(("who ", "who's", "whose")):
        answer_type = "PERSON"
        explanation = "Expects a person or entity name"
    elif question_lower.startswith(("where ", "where's")):
        answer_type = "PLACE/LOCATION"
        explanation = "Expects a location or place"
    elif question_lower.startswith(("when ", "when's")):
        answer_type = "TIME/DATE"
        explanation = "Expects a time or date"
    elif question_lower.startswith(("how many", "how much")):
        answer_type = "NUMBER/QUANTITY"
        explanation = "Expects a numeric answer"
    elif question_lower.startswith(
        (
            "is ",
            "are ",
            "was ",
            "were ",
            "do ",
            "does ",
            "did ",
            "can ",
            "could ",
            "would ",
            "should ",
        )
    ):
        answer_type = "YES/NO"
        explanation = "Expects a yes/no answer (may include explanation)"
    elif question_lower.startswith(("why ", "how ")):
        answer_type = "EXPLANATION"
        explanation = "Expects a detailed explanation or reasoning"
    elif question_lower.startswith(("what ", "what's")):
        if "definition" in question_lower or "mean" in question_lower:
            answer_type = "DEFINITION"
            explanation = "Expects a definition or meaning"
        else:
            answer_type = "DESCRIPTION/ENTITY"
            explanation = "Expects a description or entity identification"
    else:
        answer_type = "GENERAL"
        explanation = "General question, answer format not strictly defined"

    return (
        f"Question: {question}\n\n"
        f"Expected Answer Type: {answer_type}\n"
        f"Explanation: {explanation}\n\n"
        f"Recommended Strategy: "
        + (
            "Search for entity/person name"
            if answer_type == "PERSON"
            else (
                "Search for location information"
                if answer_type == "PLACE/LOCATION"
                else (
                    "Search for temporal information"
                    if answer_type == "TIME/DATE"
                    else (
                        "Extract numeric information"
                        if answer_type == "NUMBER/QUANTITY"
                        else (
                            "Verify facts for binary answer"
                            if answer_type == "YES/NO"
                            else (
                                "Gather comprehensive explanation"
                                if answer_type == "EXPLANATION"
                                else (
                                    "Retrieve definition"
                                    if answer_type == "DEFINITION"
                                    else "General knowledge retrieval"
                                )
                            )
                        )
                    )
                )
            )
        )
    )
