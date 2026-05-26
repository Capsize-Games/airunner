"""Daemon-backed evals for automatic agent mood updates."""

from __future__ import annotations

import pytest

from airunner_model.models.conversation import Conversation

from api.tests.eval.agent_eval_support import build_agent_request
from api.tests.eval.agent_eval_support import run_agent_eval_case
from api.tests.llm_functional_support import combined_llama_env_overrides
from api.tests.llm_functional_support import daemon_env
from api.tests.llm_functional_support import llm_artifact_path
from api.tests.llm_functional_support import started_daemon
from api.tests.llm_functional_support import wait_for_log_text


_MODEL_ID = "qwen3.5-9b"
_MOOD_CASES = [
    pytest.param(
        "thanks, that was really helpful",
        "happy",
        id="happy",
    ),
    pytest.param(
        "this is stupid and I hate it",
        "frustrated",
        id="frustrated",
    ),
    pytest.param(
        "I am confused and do not understand what you mean",
        "confused",
        id="confused",
    ),
]


def _mood_daemon_env() -> dict[str, str]:
    """Return daemon env overrides for deterministic mood evals."""
    extra_env = combined_llama_env_overrides(_MODEL_ID)
    extra_env.update(
        {
            "AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS": "1",
            "AIRUNNER_LLM_PRINT_SYSTEM_PROMPT": "1",
        }
    )
    return daemon_env(
        extra_env=extra_env,
    )


def _seed_conversation() -> int:
    """Create one persisted conversation with a prior user turn."""
    conversation = Conversation.create()
    assert conversation is not None
    Conversation.objects.update(
        conversation.id,
        value=[{"role": "user", "content": "Hello there."}],
    )
    return int(conversation.id)


@pytest.mark.parametrize(("prompt", "expected_mood"), _MOOD_CASES)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
def test_agent_updates_mood_from_followup_turn(
    prompt: str,
    expected_mood: str,
) -> None:
    """Update agent mood from one persisted prior user turn."""
    artifact_path = llm_artifact_path(_MODEL_ID)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    conversation_id = _seed_conversation()
    with started_daemon(_mood_daemon_env()) as daemon:
        payload = build_agent_request(
            _MODEL_ID,
            prompt,
            tool_categories=[],
            use_memory=True,
            conversation_id=conversation_id,
            max_new_tokens=32,
        )
        result = run_agent_eval_case(daemon.base_url, payload)
        assert result.status_code == 200, result.payload
        wait_for_log_text(
            daemon.log_path,
            f"[AUTO MOOD] Updated to: {expected_mood}",
        )