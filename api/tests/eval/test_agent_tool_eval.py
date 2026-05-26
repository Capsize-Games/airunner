"""Daemon-backed evals for deterministic individual tool usage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import pytest

from api.tests.eval.agent_eval_support import AgentEvalResult
from api.tests.eval.agent_eval_support import assert_success
from api.tests.eval.agent_eval_support import assert_tool_names
from api.tests.eval.agent_eval_support import build_agent_request
from api.tests.eval.agent_eval_support import run_agent_eval_case
from api.tests.llm_functional_support import combined_llama_env_overrides
from api.tests.llm_functional_support import daemon_env
from api.tests.llm_functional_support import llm_artifact_path
from api.tests.llm_functional_support import started_daemon

_MODEL_IDS = ["qwen3.5-9b", "gpt-oss-20b"]
_Validator = Callable[[AgentEvalResult, Any], None]


def _tool_daemon_env(model_id: str) -> dict[str, str]:
    """Return stable daemon env overrides for tool-usage evals."""
    return daemon_env(
        llm_on=True,
        tts_on=False,
        extra_env=combined_llama_env_overrides(model_id),
    )


def _assert_clear_history_result(
    result: AgentEvalResult,
    log_path: Any,
) -> None:
    """Assert that the clear-history tool was executed and reported."""
    assert_tool_names(
        result,
        expected={"clear_chat_history"},
        log_path=log_path,
    )
    assert "clear_chat_history" in result.visible_message, result.payload
    assert "did not make any changes" in result.visible_message.lower(), (
        result.payload
    )


def _assert_datetime_result(
    result: AgentEvalResult,
    log_path: Any,
) -> None:
    """Assert that the datetime tool returned the current local year."""
    current_year = str(datetime.now().astimezone().year)
    assert_tool_names(
        result,
        expected={"get_current_datetime"},
        log_path=log_path,
    )
    assert current_year in result.visible_message, result.payload
    assert "current local date and time:" in result.visible_message.lower(), (
        result.payload
    )


_TOOL_CASES = [
    pytest.param(
        (
            "Use the clear chat history tool."
        ),
        ["conversation"],
        "clear_chat_history",
        16,
        _assert_clear_history_result,
        id="forced-clear-chat-history",
    ),
    pytest.param(
        "Use the current date and time tool.",
        ["system"],
        "get_current_datetime",
        32,
        _assert_datetime_result,
        id="forced-current-datetime",
    ),
]


@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
@pytest.mark.parametrize(
    ("prompt", "tool_categories", "force_tool", "max_new_tokens",
     "validator"),
    _TOOL_CASES,
)
def test_agent_forced_tool_usage(
    model_id: str,
    prompt: str,
    tool_categories: list[str],
    force_tool: str,
    max_new_tokens: int,
    validator: _Validator,
) -> None:
    """Validate one deterministic forced tool invocation and reply."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    payload = build_agent_request(
        model_id,
        prompt,
        tool_categories=tool_categories,
        force_tool=force_tool,
        max_new_tokens=max_new_tokens,
    )
    with started_daemon(_tool_daemon_env(model_id)) as daemon:
        result = run_agent_eval_case(daemon.base_url, payload)
        assert_success(result, daemon.log_path)
        validator(result, daemon.log_path)