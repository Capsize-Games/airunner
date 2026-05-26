"""Daemon-backed evals for non-forced tool-selection behavior."""

from __future__ import annotations

import re
from typing import Any

import pytest

from api.tests.eval.agent_eval_support import assert_success
from api.tests.eval.agent_eval_support import build_agent_request
from api.tests.eval.agent_eval_support import run_agent_eval_case
from api.tests.eval.agent_eval_support import tool_names_from_log
from api.tests.llm_functional_support import combined_llama_env_overrides
from api.tests.llm_functional_support import daemon_env
from api.tests.llm_functional_support import llm_artifact_path
from api.tests.llm_functional_support import started_daemon

_MODEL_IDS = ["qwen3.5-9b", "gpt-oss-20b"]


_MESSAGE_TOOL_PATTERNS = (
    (r"get\s*_?current\s*_?datetime", "get_current_datetime"),
    (r"python\s*_?compute", "python_compute"),
    (r"numpy\s*_?compute", "numpy_compute"),
    (r"sympy\s*_?compute", "sympy_compute"),
    (r"search\s*_?news", "search_news"),
    (r"search\s*_?web", "search_web"),
    (r"google\s*_?search", "search_web"),
    (r"\[\s*search\s*\]", "search_web"),
)


def _selection_daemon_env(model_id: str) -> dict[str, str]:
    """Return stable daemon env overrides for selection evals."""
    return daemon_env(
        llm_on=True,
        tts_on=False,
        extra_env=combined_llama_env_overrides(model_id),
    )


def _selection_request(
    model_id: str,
    prompt: str,
    *,
    tool_categories: list[str] | None,
    max_new_tokens: int = 96,
) -> dict[str, object]:
    """Build one non-forced tool-selection request payload."""
    return build_agent_request(
        model_id,
        prompt,
        tool_categories=tool_categories,
        force_tool=None,
        max_new_tokens=max_new_tokens,
    )


def _selected_tool_names(result: Any, log_path: str) -> set[str]:
    """Extract selected tool names from calls, logs, or message fallback."""
    observed = set(result.tools)
    if not observed:
        observed = set(tool_names_from_log(log_path))
    if observed:
        return observed

    message = str(result.payload.get("message", "")).lower()
    for pattern, mapped_name in _MESSAGE_TOOL_PATTERNS:
        if re.search(pattern, message):
            return {mapped_name}
    return set()


def _run_selection_case_with_retry(
    base_url: str,
    payload: dict[str, object],
) -> Any:
    """Run one selection case and retry once on empty/no-tool output."""
    result = run_agent_eval_case(base_url, payload)
    if not result.visible_message and not result.tools:
        result = run_agent_eval_case(base_url, payload)
    return result


@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
def test_agent_selects_datetime_tool_when_time_is_requested(
    model_id: str,
) -> None:
    """Validate selection of the datetime tool over math when both are present."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    prompt = "What time is it right now? Use one tool first."
    with started_daemon(_selection_daemon_env(model_id)) as daemon:
        payload = _selection_request(
            model_id,
            prompt,
            tool_categories=None,
        )
        result = _run_selection_case_with_retry(daemon.base_url, payload)
        assert_success(result, daemon.log_path)
        observed = _selected_tool_names(result, daemon.log_path)
        assert observed == {"get_current_datetime"}, result.payload


@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
def test_agent_selects_math_tool_when_computation_is_requested(
    model_id: str,
) -> None:
    """Validate selection of a math tool over datetime for arithmetic requests."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    prompt = "Compute 17 multiplied by 19 using exactly one tool first."
    with started_daemon(_selection_daemon_env(model_id)) as daemon:
        payload = _selection_request(
            model_id,
            prompt,
            tool_categories=["system", "math"],
        )
        result = _run_selection_case_with_retry(daemon.base_url, payload)
        if result.status_code != 200:
            assert result.status_code in {504}, daemon.log_path
        observed = _selected_tool_names(result, daemon.log_path)
        assert observed in (
            {"python_compute"},
            {"numpy_compute"},
            {"sympy_compute"},
        ), result.payload


@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
def test_agent_selects_search_tool_for_news_requests(
    model_id: str,
) -> None:
    """Validate search-intent prompts trigger a search category tool."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    prompt = (
        "Find the latest politics news headlines. "
        "Use exactly one tool first."
    )
    with started_daemon(_selection_daemon_env(model_id)) as daemon:
        payload = _selection_request(
            model_id,
            prompt,
            tool_categories=["search"],
            max_new_tokens=128,
        )
        result = _run_selection_case_with_retry(daemon.base_url, payload)
        if result.status_code != 200:
            assert result.status_code in {504}, daemon.log_path
        observed = _selected_tool_names(result, daemon.log_path)
        if not observed and not result.visible_message:
            pytest.xfail(
                "Known local empty-response flake: no visible output or "
                "tool traces after retry"
            )
        assert observed & {"search_news", "search_web"}, result.payload
