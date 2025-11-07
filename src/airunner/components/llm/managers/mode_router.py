"""
Mode-based routing for LLM agents.

This module implements intent classification to route user queries to
specialized subgraphs based on detected mode (AUTHOR, CODE, RESEARCH, QA).
"""

from typing import Literal, Any
from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Mode type literal for type safety
Mode = Literal["author", "code", "research", "qa", "general"]


class UserIntent(TypedDict):
    """
    Represents classified user intent.

    Attributes:
        mode: The detected mode (author/code/research/qa/general)
        confidence: Confidence score (0.0-1.0)
        reasoning: Brief explanation of classification
    """

    mode: Mode
    confidence: float
    reasoning: str


# Intent classification prompt
INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for a multi-mode AI assistant.

Your task is to analyze the user's query and determine which specialized mode would best handle it:

**AUTHOR MODE** - Creative writing, content creation, editing
- Writing stories, articles, essays, poetry
- Improving writing style, grammar, clarity
- Generating content ideas, outlines
- Editing and proofreading

**CODE MODE** - Programming, software development
- Writing code in any language
- Debugging, testing, code review
- Explaining code concepts
- File operations related to code

**RESEARCH MODE** - Information gathering, synthesis, analysis
- Searching for information
- Synthesizing multiple sources
- Comparing viewpoints
- Organizing research findings

**QA MODE** - Direct question answering, factual queries
- Answering specific questions
- Fact checking
- Explaining concepts
- Providing definitions

**GENERAL MODE** - Everything else
- Casual conversation
- Unclear/ambiguous requests
- Multi-mode tasks
- Anything not clearly fitting above modes

Based on the user's query, respond with:
1. mode: One of [author, code, research, qa, general]
2. confidence: 0.0-1.0 (how certain you are)
3. reasoning: Brief explanation (1-2 sentences)

User query: {query}

Respond in this exact format:
MODE: <mode>
CONFIDENCE: <0.0-1.0>
REASONING: <explanation>
"""


def parse_intent_response(response: str) -> UserIntent:
    """
    Parse LLM response into UserIntent structure.

    Args:
        response: Raw LLM response text

    Returns:
        UserIntent with parsed mode, confidence, reasoning
    """
    lines = response.strip().split("\n")
    mode = "general"
    confidence = 0.5
    reasoning = "Could not parse intent classification"

    for line in lines:
        line = line.strip()
        if line.startswith("MODE:"):
            mode_str = line.replace("MODE:", "").strip().lower()
            if mode_str in ["author", "code", "research", "qa", "general"]:
                mode = mode_str  # type: ignore
        elif line.startswith("CONFIDENCE:"):
            try:
                confidence = float(line.replace("CONFIDENCE:", "").strip())
                confidence = max(0.0, min(1.0, confidence))
            except ValueError:
                logger.warning(f"Could not parse confidence: {line}")
        elif line.startswith("REASONING:"):
            reasoning = line.replace("REASONING:", "").strip()

    return UserIntent(mode=mode, confidence=confidence, reasoning=reasoning)


def classify_intent(
    query: str, chat_model: Any, threshold: float = 0.6
) -> UserIntent:
    """
    Classify user query intent using LLM.

    Args:
        query: User's query text
        chat_model: LangChain chat model for classification
        threshold: Confidence threshold for specialized modes (default 0.6)

    Returns:
        UserIntent with mode, confidence, reasoning
    """
    prompt = ChatPromptTemplate.from_template(INTENT_CLASSIFICATION_PROMPT)
    chain = prompt | chat_model

    try:
        response = chain.invoke({"query": query})
        response_text = (
            response.content if hasattr(response, "content") else str(response)
        )
        intent = parse_intent_response(response_text)

        logger.info(
            f"Intent classified: {intent['mode']} "
            f"(confidence: {intent['confidence']:.2f}) - "
            f"{intent['reasoning']}"
        )

        # Fall back to general mode if confidence too low
        if intent["mode"] != "general" and intent["confidence"] < threshold:
            logger.info(
                f"Confidence {intent['confidence']:.2f} below "
                f"threshold {threshold}, falling back to general mode"
            )
            intent["mode"] = "general"

        return intent

    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return UserIntent(
            mode="general",
            confidence=0.0,
            reasoning=f"Classification error: {str(e)}",
        )


def intent_classifier_node(state: dict, chat_model: Any) -> dict:
    """
    LangGraph node function for intent classification.

    Args:
        state: Current graph state (must contain 'messages')
        chat_model: LangChain chat model

    Returns:
        Updated state with 'intent' field
    """
    messages = state.get("messages", [])
    if not messages:
        logger.warning("No messages in state, using general mode")
        return {
            "intent": UserIntent(
                mode="general",
                confidence=1.0,
                reasoning="No messages to classify",
            )
        }

    # Get the last user message
    last_user_msg = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg
            break

    if not last_user_msg:
        logger.warning("No user message found, using general mode")
        return {
            "intent": UserIntent(
                mode="general",
                confidence=1.0,
                reasoning="No user message found",
            )
        }

    query = (
        last_user_msg.content
        if hasattr(last_user_msg, "content")
        else str(last_user_msg)
    )

    intent = classify_intent(query, chat_model)

    return {"intent": intent}


def route_by_intent(state: dict) -> str:
    """
    Routing function to determine which subgraph to invoke.

    Args:
        state: Current graph state (must contain 'intent')

    Returns:
        Node name to route to (author/code/research/qa/general)
    """
    intent = state.get("intent")
    if not intent:
        logger.warning("No intent in state, routing to general")
        return "general"

    mode = intent.get("mode", "general")
    logger.info(f"Routing to {mode} mode")
    return mode
