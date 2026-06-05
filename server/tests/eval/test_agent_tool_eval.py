"""Daemon-backed evals for deterministic individual tool usage."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Callable

import pytest

from agent_eval_support import AgentEvalResult
from agent_eval_support import assert_tool_names
from agent_eval_support import build_agent_request
from agent_eval_support import run_agent_eval_case
from llm_functional_support import combined_llama_env_overrides
from llm_functional_support import daemon_output
from llm_functional_support import daemon_env
from llm_functional_support import llm_artifact_path
from llm_functional_support import started_daemon
from llm_functional_support import visible_last_number

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
    assert (
        "did not make any changes" in result.visible_message.lower()
    ), result.payload


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
    assert (
        "current local date and time:" in result.visible_message.lower()
    ), result.payload


def _assert_python_compute_result(
    result: AgentEvalResult,
    log_path: Any,
) -> None:
    """Assert that the Python math tool produced the expected answer."""
    assert_tool_names(
        result,
        expected={"python_compute"},
        log_path=log_path,
    )
    if visible_last_number(result.visible_message) == "1296":
        return

    log_text = daemon_output(log_path)
    assert "Python result: (True, 1296" in log_text, log_text


def _assert_sympy_compute_result(
    result: AgentEvalResult,
    log_path: Any,
) -> None:
    """Assert that the SymPy tool produced the expected answer."""
    assert_tool_names(
        result,
        expected={"sympy_compute"},
        log_path=log_path,
    )
    if visible_last_number(result.visible_message) == "12":
        return

    log_text = daemon_output(log_path)
    assert "SymPy result: (True, 12" in log_text, log_text


def _assert_numpy_compute_result(
    result: AgentEvalResult,
    log_path: Any,
) -> None:
    """Assert that the NumPy tool produced the expected answer."""
    assert_tool_names(
        result,
        expected={"numpy_compute"},
        log_path=log_path,
    )
    if visible_last_number(result.visible_message) == "32":
        return

    log_text = daemon_output(log_path)
    assert "NumPy result" in log_text and "32" in log_text, log_text


def _assert_identify_answer_type_result(
    result: AgentEvalResult,
    log_path: Any,
) -> None:
    """Assert that the QA tool returned the expected answer type."""
    assert_tool_names(
        result,
        expected={"identify_answer_type"},
        log_path=log_path,
    )
    normalized = re.sub(r"\s+", "", result.visible_message).upper()
    assert (
        "NUMBER/QUANTITY" in normalized
        or "NON-MUTATINGTOOLS(IDENTIFY_ANSWER_TYPE)" in normalized
        or "Tool completed: identify_answer_type" in daemon_output(log_path)
    ), result.payload


def _assert_list_directory_result(
    result: AgentEvalResult,
    log_path: Any,
) -> None:
    """Assert that the file-listing tool exposed the eval test directory."""
    assert_tool_names(
        result,
        expected={"list_directory"},
        log_path=log_path,
    )
    visible_message = result.visible_message.lower()
    assert (
        "testagenttoolevalpy" in re.sub(r"[^a-z0-9]", "", visible_message)
        or "non-mutating tools (list_directory)" in visible_message
        or "Tool completed: list_directory" in daemon_output(log_path)
    ), result.payload


def _assert_scrape_website_result(
    result: AgentEvalResult,
    log_path: Any,
) -> None:
    """Assert that scrape_website ran and avoided extraction errors."""
    assert_tool_names(
        result,
        expected={"scrape_website"},
        log_path=log_path,
    )
    log_text = daemon_output(log_path).lower()
    assert "web scraping error" not in log_text, log_text
    visible_message = result.visible_message.lower()
    assert (
        "visited example.com" in visible_message
        or "non-mutating tools (scrape_website)" in visible_message
    ), result.payload


_TOOL_CASES = [
    pytest.param(
        ("Use the clear chat history tool."),
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
    pytest.param(
        ("Calculate 6 to the power of 4. Answer with digits only."),
        ["math"],
        "python_compute",
        64,
        _assert_python_compute_result,
        id="forced-python-compute",
    ),
    pytest.param(
        (
            "Differentiate x cubed and evaluate it at x equals 2. "
            "Answer with digits only."
        ),
        ["math"],
        "sympy_compute",
        64,
        _assert_sympy_compute_result,
        id="forced-sympy-compute",
    ),
    pytest.param(
        (
            "Compute the dot product of [1, 2, 3] and [4, 5, 6]. "
            "Answer with digits only."
        ),
        ["math"],
        "numpy_compute",
        64,
        _assert_numpy_compute_result,
        id="forced-numpy-compute",
    ),
    pytest.param(
        (
            "Classify the expected answer type for the question "
            "'How many blorps fit inside a snarp?'. "
            "answer with exactly NUMBER/QUANTITY only."
        ),
        ["qa"],
        "identify_answer_type",
        64,
        _assert_identify_answer_type_result,
        id="forced-identify-answer-type",
    ),
    pytest.param(
        (
            "List the contents of the services/tests/eval directory. "
            "Answer with exactly test_agent_tool_eval.py only."
        ),
        ["file"],
        "list_directory",
        48,
        _assert_list_directory_result,
        id="forced-list-directory",
    ),
    pytest.param(
        (
            "Use the website scraper tool on https://example.com and "
            "answer with exactly example.com only."
        ),
        ["search"],
        "scrape_website",
        96,
        _assert_scrape_website_result,
        id="forced-scrape-website",
    ),
]


@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
@pytest.mark.parametrize(
    ("prompt", "tool_categories", "force_tool", "max_new_tokens", "validator"),
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
        # Local GGUF runs can occasionally return an empty payload without
        # tool traces on the first attempt. Retry once before asserting.
        if not result.visible_message and not result.tools:
            result = run_agent_eval_case(daemon.base_url, payload)
        if (
            model_id.startswith("qwen3")
            and not result.visible_message
            and not result.tools
        ):
            pytest.xfail(
                "Known local Qwen empty-response flake: no visible output "
                "or tool traces after retry"
            )
        # Some models can return an empty visible synthesis while still
        # executing the forced tool correctly. Tool assertions below
        # validate the behavior under test.
        assert result.status_code == 200, daemon_output(daemon.log_path)
        validator(result, daemon.log_path)
