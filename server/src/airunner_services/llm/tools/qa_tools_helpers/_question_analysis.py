"""Question analysis helpers for QA tools."""

QUESTION_PATTERNS = [
    (("who ", "who's", "whose"), "PERSON", "Expects a person or entity name"),
    (("where ", "where's"), "PLACE/LOCATION", "Expects a location or place"),
    (("when ", "when's"), "TIME/DATE", "Expects a time or date"),
    (("how many", "how much"), "NUMBER/QUANTITY", "Expects a numeric answer"),
    ((
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
    ), "YES/NO", "Expects a yes/no answer (may include explanation)"),
    (("why ", "how "), "EXPLANATION", "Expects a detailed explanation or reasoning"),
]

ANSWER_STRATEGIES = {
    "PERSON": "Search for entity/person name",
    "PLACE/LOCATION": "Search for location information",
    "TIME/DATE": "Search for temporal information",
    "NUMBER/QUANTITY": "Extract numeric information",
    "YES/NO": "Verify facts for binary answer",
    "EXPLANATION": "Gather comprehensive explanation",
    "DEFINITION": "Retrieve definition",
    "DESCRIPTION/ENTITY": "General knowledge retrieval",
    "GENERAL": "General knowledge retrieval",
}

DEFAULT_QUESTIONS = [
    "What aspect of this topic interests you most?",
    "Are you looking for a specific type of information?",
    "Is there any context that would help me answer better?",
]


def generate_clarifying_questions_impl(query: str, num_questions: int = 3) -> str:
    """Generate clarifying questions for an ambiguous query."""
    questions = _specific_clarifying_questions(query)
    _fill_default_questions(questions, num_questions)
    question_lines = "\n".join(
        f"{index}. {item}"
        for index, item in enumerate(questions[:num_questions], 1)
    )
    return f"Query: {query}\n\nClarifying Questions:\n{question_lines}"


def identify_answer_type_impl(question: str) -> str:
    """Describe the expected answer type for a question."""
    answer_type, explanation = _answer_type_details(question.lower())
    strategy = ANSWER_STRATEGIES[answer_type]
    return (
        f"Question: {question}\n\n"
        f"Expected Answer Type: {answer_type}\n"
        f"Explanation: {explanation}\n\n"
        f"Recommended Strategy: {strategy}"
    )


def _specific_clarifying_questions(query: str) -> list[str]:
    """Return ambiguity-specific clarifying questions."""
    words = query.lower().split()
    questions: list[str] = []
    if any(word in words for word in ["it", "this", "that", "they", "them"]):
        questions.append("What specifically are you referring to?")
    if any(word in words for word in ["thing", "stuff", "something", "some"]):
        questions.append("Could you be more specific about what you're asking about?")
    if any(word in words for word in ["recent", "latest", "new", "old"]):
        questions.append("What time period are you interested in?")
    return questions


def _fill_default_questions(questions: list[str], num_questions: int) -> None:
    """Pad a question list with general clarifiers up to the target size."""
    while len(questions) < num_questions:
        questions.append(DEFAULT_QUESTIONS[len(questions) % len(DEFAULT_QUESTIONS)])


def _answer_type_details(question_lower: str) -> tuple[str, str]:
    """Return the expected answer type and rationale."""
    pattern_match = _match_question_pattern(question_lower)
    if pattern_match is not None:
        return pattern_match
    if question_lower.startswith(("what ", "what's")):
        return _what_question_details(question_lower)
    return "GENERAL", "General question, answer format not strictly defined"


def _match_question_pattern(question_lower: str) -> tuple[str, str] | None:
    """Return the first matching answer type pattern."""
    for prefixes, answer_type, explanation in QUESTION_PATTERNS:
        if question_lower.startswith(prefixes):
            return answer_type, explanation
    return None


def _what_question_details(question_lower: str) -> tuple[str, str]:
    """Return the answer type details for a what-question."""
    if "definition" in question_lower or "mean" in question_lower:
        return "DEFINITION", "Expects a definition or meaning"
    return "DESCRIPTION/ENTITY", "Expects a description or entity identification"