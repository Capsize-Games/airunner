"""Helpers for daemon-backed LLM agent eval tests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from airunner_services.eval.client import AIRunnerClient
from airunner_services.eval.evaluators import create_correctness_evaluator
from airunner_services.eval.evaluators import create_relevance_evaluator

from api.tests.llm_functional_support import daemon_output
from api.tests.llm_functional_support import post_json
from api.tests.llm_functional_support import visible_llm_message


@dataclass(frozen=True)
class AgentEvalResult:
    """Collected response data for one daemon-backed eval case."""

    status_code: int
    payload: dict[str, Any]
    visible_message: str
    tools: list[str]


def build_agent_request(
    model_id: str,
    prompt: str,
    *,
    tool_categories: list[str] | None,
    rag_files: list[str] | None = None,
    use_memory: bool = False,
    conversation_id: int | None = None,
    node_id: str | None = None,
    system_prompt: str | None = None,
    force_tool: str | None = None,
    max_new_tokens: int = 128,
) -> dict[str, Any]:
    """Return one stable request payload for agent flow evals."""
    if model_id.startswith("qwen3") and not prompt.lstrip().startswith("/no_think"):
        prompt = f"/no_think\n{prompt}"

    llm_request = {
        "force_tool": force_tool,
        "max_new_tokens": max_new_tokens,
        "rag_files": rag_files,
        "tool_categories": tool_categories,
        "use_memory": use_memory,
    }
    payload = {
        "action": "CHAT",
        "do_sample": False,
        "enable_thinking": False,
        "ephemeral": not use_memory,
        "force_tool": force_tool,
        "llm_request": llm_request,
        "max_tokens": max_new_tokens,
        "model": model_id,
        "prompt": prompt,
        "rag_files": rag_files,
        "stream": False,
        "temperature": 0.1,
        "tool_categories": tool_categories,
        "top_p": 0.1,
        "use_memory": use_memory,
    }
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    if system_prompt:
        payload["system_prompt"] = system_prompt
    if node_id:
        payload["node_id"] = node_id
    return payload


def run_agent_eval_case(base_url: str, payload: dict[str, Any]) -> AgentEvalResult:
    """Execute one eval case against the daemon and return parsed data."""
    status_code, response_body, _content_type = post_json(
        f"{base_url}/llm/generate",
        payload,
    )
    response_payload = json.loads(response_body.decode("utf-8"))
    tools = list(response_payload.get("tools") or [])
    message = str(response_payload.get("message") or "")
    return AgentEvalResult(
        status_code=status_code,
        payload=response_payload,
        visible_message=visible_llm_message(message),
        tools=tools,
    )


def tool_names_from_log(log_path: Any) -> list[str]:
    """Return executed tool names parsed from one daemon log tail."""
    completed = re.findall(
        r"Tool completed: ([A-Za-z0-9_]+) - success",
        daemon_output(log_path),
    )
    return list(dict.fromkeys(completed))


def assert_success(result: AgentEvalResult, log_path: Any) -> None:
    """Assert that one daemon-backed eval request completed successfully."""
    assert result.status_code == 200, daemon_output(log_path)
    assert result.visible_message, result.payload


def assert_tool_names(
    result: AgentEvalResult,
    *,
    expected: set[str],
    log_path: Any | None = None,
) -> None:
    """Assert the executed tool names exactly match the expected set."""
    observed = set(result.tools)
    if not observed and log_path is not None:
        observed = set(tool_names_from_log(log_path))
    assert observed == expected, result.payload


def judge_against_reference(
    base_url: str,
    *,
    model_id: str,
    prompt: str,
    output_text: str,
    reference_output: str,
) -> dict[str, dict[str, Any]]:
    """Score one response with AIRunner's current judge helpers."""
    client = AIRunnerClient(base_url=base_url)
    correctness = create_correctness_evaluator(client, model=model_id)
    relevance = create_relevance_evaluator(client, model=model_id)
    return {
        "correctness": correctness(prompt, output_text, reference_output),
        "relevance": relevance(prompt, output_text, reference_output),
    }


def assert_judged_quality(
    scores: dict[str, dict[str, Any]],
    *,
    minimum: float,
) -> None:
    """Assert that all requested judge metrics meet one threshold."""
    for metric_name, metric in scores.items():
        score = float(metric.get("score") or 0.0)
        assert score >= minimum, (
            f"{metric_name} score {score:.2f} below {minimum:.2f}: "
            f"{metric.get('reasoning', '')}"
        )
