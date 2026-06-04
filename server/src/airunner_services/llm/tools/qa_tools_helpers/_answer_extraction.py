"""Answer extraction helpers for QA tools."""


def extract_answer_from_context_impl(question: str, context: str) -> str:
    """Extract the best matching answer sentence from context."""
    question_words = _significant_question_words(question)
    sentences = _context_sentences(context)
    scored_sentences = _score_sentences(question_words, sentences)
    if not scored_sentences:
        return f"Could not find answer to '{question}' in provided context."
    best_score, best_match = scored_sentences[0]
    confidence = _extraction_confidence(best_score)
    return (
        f"Question: {question}\n\n"
        f"Extracted Answer: {best_match}\n\n"
        f"Confidence: {confidence}\n"
        f"Location: Found in context"
    )


def rank_answer_candidates_impl(question: str, candidates: list[str]) -> str:
    """Rank answer candidates using keyword overlap and length bonuses."""
    if not candidates:
        return "No candidates provided to rank."
    question_words = _significant_question_words(question)
    scored_candidates = _score_candidates(question_words, candidates)
    return _format_ranked_candidates(question, scored_candidates)


def _significant_question_words(question: str) -> set[str]:
    """Return lowercase question words longer than three characters."""
    return {word.lower() for word in question.split() if len(word) > 3}


def _context_sentences(context: str) -> list[str]:
    """Split context into lightly normalized sentence candidates."""
    normalized = context.replace("! ", ".|").replace("? ", ".|")
    return normalized.split(".|")


def _score_sentences(
    question_words: set[str],
    sentences: list[str],
) -> list[tuple[int, str]]:
    """Score sentences by overlap with significant question words."""
    scored: list[tuple[int, str]] = []
    for sentence in sentences:
        overlap = question_words & {word.lower() for word in sentence.split()}
        if overlap:
            scored.append((len(overlap), sentence.strip()))
    scored.sort(reverse=True)
    return scored


def _extraction_confidence(score: int) -> str:
    """Return the extraction confidence label for a sentence score."""
    if score > 2:
        return f"High ({score} matching terms)"
    return "Moderate"


def _score_candidates(
    question_words: set[str],
    candidates: list[str],
) -> list[tuple[int, int, str]]:
    """Score candidates by keyword overlap and preferred length."""
    scored: list[tuple[int, int, str]] = []
    for index, candidate in enumerate(candidates):
        candidate_words = {word.lower() for word in candidate.split()}
        overlap = question_words & candidate_words
        score = len(overlap) * 10 + _length_bonus(candidate)
        scored.append((score, index, candidate))
    scored.sort(reverse=True)
    return scored


def _length_bonus(candidate: str) -> int:
    """Return the moderate-length bonus for a candidate answer."""
    word_count = len(candidate.split())
    if 20 < word_count < 100:
        return 5
    return 0


def _format_ranked_candidates(
    question: str,
    scored_candidates: list[tuple[int, int, str]],
) -> str:
    """Format ranked candidate answers for the QA tool response."""
    result = f"Question: {question}\n\nRanked Answers:\n\n"
    for rank, (score, _, candidate) in enumerate(scored_candidates, 1):
        preview = candidate[:150]
        suffix = "..." if len(candidate) > 150 else ""
        result += f"{rank}. [Score: {score}] {preview}{suffix}\n\n"
    return result