"""Verification node helpers for the long-running Session Agent."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.llm.long_running.session_agent_state import (
    SessionPhase,
    SessionWorkflowState,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _steps_text(feature: Any) -> str:
    """Return checkbox-formatted verification steps."""
    return "\n".join(
        f"- [ ] {step}" for step in (feature.verification_steps or [])
    )


def _verification_prompt(feature: Any) -> str:
    """Return the verification prompt for one feature."""
    return f"""# Verification Phase

Feature: {feature.name}

Please verify this feature by completing these steps:
{_steps_text(feature)}

For each step:
1. Execute the verification action
2. Check the result
3. Mark as passed or failed

If ALL steps pass, mark the feature as PASSING.
If ANY step fails, note what went wrong.

CRITICAL: Only mark as passing if you have ACTUALLY VERIFIED each step!"""


def _verification_result(content: str) -> tuple[str, bool]:
    """Return the verification result and continuation flag."""
    passed = any(
        phrase in content
        for phrase in [
            "all steps pass",
            "verification passed",
            "feature passing",
            "all tests pass",
        ]
    )
    failed = any(
        phrase in content
        for phrase in [
            "verification failed",
            "step failed",
            "test failed",
            "does not work",
        ]
    )
    return ("passed" if passed else "failed", not passed and not failed)


def _verification_response(
    agent: Any,
    state: SessionWorkflowState,
    feature: Any,
) -> dict[str, Any]:
    """Invoke the model for one verification step."""
    response = agent._chat_model.invoke(
        state["messages"]
        + [HumanMessage(content=_verification_prompt(feature))]
    )
    result, should_continue = _verification_result(response.content.lower())
    return {
        "messages": [response],
        "verification_result": result,
        "phase": SessionPhase.CLEANUP,
        "should_continue": should_continue,
    }


def verification_node(
    agent: Any,
    state: SessionWorkflowState,
) -> dict[str, Any]:
    """Verify the implemented feature."""
    logger.info("Verification phase for feature %s", state.get("feature_id"))
    feature = agent._project_manager.get_feature(state["feature_id"])
    if feature is None:
        return {"error": "Feature not found", "should_continue": False}
    try:
        return _verification_response(agent, state, feature)
    except Exception as error:
        logger.error("Verification error: %s", error)
        return {"error": str(error), "should_continue": False}


# Verification is isolated so prompt wording and pass/fail heuristics remain in
# one place.
# Cleanup can then treat verification output as a single normalized result.
# The result parser stays adjacent to the prompt so verification language and
# continuation behavior can evolve together.
