"""Daemon-backed evals for judged agent response quality."""

from __future__ import annotations

import pytest

from api.tests.eval.agent_eval_support import assert_judged_quality
from api.tests.eval.agent_eval_support import assert_success
from api.tests.eval.agent_eval_support import build_agent_request
from api.tests.eval.agent_eval_support import judge_against_reference
from api.tests.eval.agent_eval_support import run_agent_eval_case
from api.tests.llm_functional_support import combined_llama_env_overrides
from api.tests.llm_functional_support import daemon_env
from api.tests.llm_functional_support import llm_artifact_path
from api.tests.llm_functional_support import started_daemon

_MODEL_IDS = ["qwen3.5-9b", "gpt-oss-20b"]
_QUALITY_CASES = [
    pytest.param(
        "Reply with exactly: alpha.",
        "Reply with exactly the word alpha.",
        "alpha",
        id="plain-chat",
    ),
    pytest.param(
        "Reply with exactly: alpha!",
        (
            "You are a cheerful assistant. Reply with exactly the "
            "phrase 'alpha!'."
        ),
        "alpha!",
        id="personality-prompt",
    ),
]


def _response_daemon_env(model_id: str) -> dict[str, str]:
    """Return stable daemon env overrides for judged response evals."""
    return daemon_env(
        llm_on=True,
        tts_on=False,
        extra_env=combined_llama_env_overrides(model_id),
    )


def _judge_input(prompt: str, system_prompt: str | None) -> str:
    """Return the combined judge input for one response case."""
    if not system_prompt:
        return f"User prompt: {prompt}"
    return (
        f"System prompt: {system_prompt}\n"
        f"User prompt: {prompt}"
    )


@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
@pytest.mark.parametrize(
    ("prompt", "system_prompt", "reference_output"),
    _QUALITY_CASES,
)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
def test_agent_response_quality_against_reference(
    model_id: str,
    prompt: str,
    system_prompt: str | None,
    reference_output: str,
) -> None:
    """Judge one final agent response against a short reference answer."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    with started_daemon(_response_daemon_env(model_id)) as daemon:
        payload = build_agent_request(
            model_id,
            prompt,
            tool_categories=[],
            system_prompt=system_prompt,
            max_new_tokens=16,
        )
        result = run_agent_eval_case(daemon.base_url, payload)
        assert_success(result, daemon.log_path)

        scores = judge_against_reference(
            daemon.base_url,
            model_id=model_id,
            prompt=_judge_input(prompt, system_prompt),
            output_text=result.visible_message,
            reference_output=reference_output,
        )
        assert_judged_quality(scores, minimum=0.7)

        if reference_output.endswith("!"):
            assert result.visible_message.endswith("!"), (
                result.payload
            )