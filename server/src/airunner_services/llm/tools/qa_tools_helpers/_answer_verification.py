"""Answer verification helpers for QA tools."""

from typing import List


def verify_answer_impl(question: str, answer: str, context: str = "") -> str:
    """Build the answer verification response."""
    answer_words = _significant_words(answer)
    context_words = _significant_words(context)
    overlap_count = len(answer_words & context_words) if context else 0
    confidence = _verification_confidence(
        answer_words,
        context_words,
        has_context=bool(context),
    )
    return _format_verification(
        question,
        answer,
        context,
        confidence,
        overlap_count,
    )


def score_answer_confidence_impl(
    answer: str,
    sources: List[str] | None = None,
    reasoning: str = "",
) -> str:
    """Build the answer confidence score response."""
    source_list = sources or []
    confidence = min(_base_confidence(answer, source_list, reasoning), 100)
    factors = _confidence_factors(answer, source_list, reasoning)
    recommendation = _confidence_recommendation(confidence)
    factor_lines = "\n".join(f"  {factor}" for factor in factors)
    return (
        f"Answer Confidence Score: {confidence}/100\n\n"
        f"Factors:\n{factor_lines}\n\n"
        f"Recommendation: {recommendation}"
    )


def _significant_words(text: str) -> set[str]:
    """Return lowercase words longer than four characters."""
    return {word.lower() for word in text.split() if len(word) > 4}


def _verification_confidence(
    answer_words: set[str],
    context_words: set[str],
    has_context: bool,
) -> float:
    """Calculate overlap-based confidence for an answer."""
    if not has_context:
        return 50.0
    overlap = answer_words & context_words
    raw_score = len(overlap) / max(len(answer_words), 1) * 100
    return min(raw_score, 100)


def _format_verification(
    question: str,
    answer: str,
    context: str,
    confidence: float,
    overlap_count: int,
) -> str:
    """Format the answer verification tool response."""
    evidence = _verification_evidence(context, overlap_count)
    response = (
        f"Answer Verification:\n\n"
        f"Question: {question}\n"
        f"Answer: {_preview(answer, 200)}\n\n"
        f"Confidence: {confidence:.1f}%\n"
        f"Evidence: {evidence}\n\n"
    )
    response += _supporting_context(context, confidence)
    response += _verification_warning(confidence)
    return response


def _verification_evidence(context: str, overlap_count: int) -> str:
    """Describe the evidence that supported verification."""
    if not context:
        return "No context provided"
    return f"Found {overlap_count} supporting terms in context"


def _preview(text: str, limit: int) -> str:
    """Return a truncated preview string."""
    suffix = "..." if len(text) > limit else ""
    return f"{text[:limit]}{suffix}"


def _supporting_context(context: str, confidence: float) -> str:
    """Return the optional supporting context section."""
    if not context or confidence <= 50:
        return ""
    return f"Supporting context: {context[:200]}..."


def _verification_warning(confidence: float) -> str:
    """Return the optional low-confidence warning line."""
    if confidence >= 60:
        return ""
    return "\nWarning: Low confidence, answer may need verification"


def _base_confidence(
    answer: str,
    sources: List[str],
    reasoning: str,
) -> int:
    """Calculate a base confidence score before clamping."""
    score = 50
    if sources:
        score += min(len(sources) * 10, 30)
    if len(answer.split()) > 50:
        score += 10
    if reasoning and len(reasoning) > 100:
        score += 10
    return score


def _confidence_factors(
    answer: str,
    sources: List[str],
    reasoning: str,
) -> List[str]:
    """List the factors that influenced the confidence score."""
    factors: List[str] = []
    if sources:
        factors.append(f"✓ Supported by {len(sources)} source(s)")
    if len(answer.split()) > 50:
        factors.append("✓ Detailed answer provided")
    if reasoning:
        factors.append("✓ Reasoning chain available")
    if not sources:
        factors.append("⚠ No source verification")
    return factors


def _confidence_recommendation(confidence: int) -> str:
    """Return a recommendation for the computed confidence score."""
    if confidence >= 80:
        return "High confidence - answer well-supported"
    if confidence >= 60:
        return "Moderate confidence - verify if critical"
    return "Low confidence - additional verification needed"
