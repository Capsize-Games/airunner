"""Daemon-backed eval tests for the baseline LLM agent flow."""

from __future__ import annotations

import pytest

from api.tests.eval.agent_eval_support import assert_success
from api.tests.eval.agent_eval_support import assert_tool_names
from api.tests.eval.agent_eval_support import build_agent_request
from api.tests.eval.agent_eval_support import run_agent_eval_case
from api.tests.llm_functional_support import combined_llama_env_overrides
from api.tests.llm_functional_support import daemon_env
from api.tests.llm_functional_support import llm_artifact_path
from api.tests.llm_functional_support import started_daemon
from api.tests.llm_functional_support import visible_last_number


_MODEL_IDS = ["qwen3.5-9b", "gpt-oss-20b"]
_TOOL_FLOW_MODEL_IDS = ["qwen3.5-9b"]


def _flow_daemon_env(model_id: str) -> dict[str, str]:
    """Return stable daemon env overrides for one flow-eval model."""
    return daemon_env(
        llm_on=True,
        tts_on=False,
        extra_env=combined_llama_env_overrides(model_id),
    )


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
def test_agent_simple_chat_flow_without_tools(model_id: str) -> None:
    """Validate the no-tool path for a constrained chat response."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    payload = build_agent_request(
        model_id,
        "Reply with exactly: alpha.",
        tool_categories=[],
        system_prompt="Reply with exactly the word alpha.",
        max_new_tokens=16,
    )
    with started_daemon(_flow_daemon_env(model_id)) as daemon:
        result = run_agent_eval_case(daemon.base_url, payload)
        assert_success(result, daemon.log_path)
        assert_tool_names(result, expected=set())
        assert "alpha" in result.visible_message.lower(), result.payload


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
@pytest.mark.parametrize(
    "model_id",
    _TOOL_FLOW_MODEL_IDS,
    ids=_TOOL_FLOW_MODEL_IDS,
)
def test_agent_forced_math_tool_flow(model_id: str) -> None:
    """Validate tool execution plus final response synthesis."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    prompt = (
        "Use the available math tool to calculate 12 multiplied by 13. "
        "After the tool result, answer with digits only."
    )
    payload = build_agent_request(
        model_id,
        prompt,
        tool_categories=["math"],
        force_tool="python_compute",
        max_new_tokens=32,
    )
    with started_daemon(_flow_daemon_env(model_id)) as daemon:
        result = run_agent_eval_case(daemon.base_url, payload)
        assert_success(result, daemon.log_path)
        assert_tool_names(
            result,
            expected={"python_compute"},
            log_path=daemon.log_path,
        )
        assert visible_last_number(str(result.payload.get("message") or "")) == "156", (
            result.payload
        )